import os
import sqlite3
from typing import TypedDict, Annotated, Sequence, Literal
import operator
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

# Import the real email dispatch function from utils
from utils import send_recovery_email as dispatch_real_email

load_dotenv()

DB_PATH = "ecommerce_ops.db"

# --- Helper Function for SQLite Audit Logging ---

def log_email_action(cart_id: str, customer_email: str, status: str):
    """Logs the recovery email dispatch status to SQLite audit table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO recovery_logs (cart_id, customer_email, status, timestamp)
            VALUES (?, ?, ?, DATETIME('now'))
            """,
            (cart_id, customer_email, status)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Note: Could not record to audit log: {e}")


# --- Tools ---

# --- READ TOOLS (Executed Automatically) ---

@tool
def get_abandoned_carts(min_hours_ago: float = 0.0) -> list[dict]:
    """Retrieves pending abandoned carts from the database where abandonment time >= min_hours_ago."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT cart_id, user_id, items_count, total_value, abandoned_hours_ago, status 
        FROM abandoned_carts 
        WHERE status = 'pending' AND abandoned_hours_ago >= ?
        """,
        (min_hours_ago,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@tool
def get_order_summary() -> dict:
    """Summarizes current order statistics including total revenue, total orders, and status breakdown."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM orders")
    total_orders, total_revenue = cursor.fetchone()

    cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    status_counts = dict(cursor.fetchall())

    conn.close()

    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "status_breakdown": status_counts
    }


@tool
def calculate_revenue_impact(abandoned_carts_count: int, avg_order_value: float) -> str:
    """Calculates potential lost revenue from abandoned checkout carts based on Average Order Value (AOV)."""
    try:
        lost_revenue = abandoned_carts_count * avg_order_value
        return f"Estimated Lost Revenue: ${lost_revenue:,.2f} based on {abandoned_carts_count} orders at AOV of ${avg_order_value:.2f}"
    except Exception as e:
        return f"Error performing calculation: {str(e)}"


# --- ACTION / WRITE TOOLS (Guarded by HITL) ---

@tool
def send_recovery_email(cart_id: str, customer_email: str, discount_code: str = "SAVE10") -> str:
    """Sends a recovery email with a discount code to a customer with an abandoned cart.
    Requires human confirmation before execution.
    """
    # 1. Trigger actual email via SMTP
    success = dispatch_real_email(
        recipient_email=customer_email,
        discount_code=discount_code,
        cart_id=cart_id
    )

    # 2. Record status to database
    status = "SUCCESS" if success else "FAILED"
    log_email_action(cart_id=cart_id, customer_email=customer_email, status=status)

    if success:
        return f"SUCCESS: Recovery email with code '{discount_code}' successfully sent to {customer_email} for cart '{cart_id}'."
    else:
        return f"FAILURE: Failed to send recovery email to {customer_email} for cart '{cart_id}'. Check SMTP configuration."


# Group tools by access tier
read_tools = [get_order_summary, get_abandoned_carts, calculate_revenue_impact]
action_tools = [send_recovery_email]
all_tools = read_tools + action_tools

# --- State ---

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intent: str

# --- Models ---

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
llm_with_tools = llm.bind_tools(all_tools)

# Pydantic schema for routing classification
class IntentClassification(BaseModel):
    intent: Literal["ops", "chat", "off_topic"] = Field(
        description="Categorize user query: 'ops' for e-commerce/analytics queries, 'chat' for greetings, 'off_topic' for non-business requests."
    )

router_llm = llm.with_structured_output(IntentClassification)

# --- Nodes ---

def router_node(state: AgentState) -> dict:
    """Classifies user intent without loading heavy tools."""
    last_msg = state["messages"][-1]
    
    # Safely extract text whether it's a tuple ("user", "text") or a BaseMessage object
    if isinstance(last_msg, tuple):
        user_text = last_msg[1]
    elif hasattr(last_msg, "content"):
        user_text = last_msg.content
    else:
        user_text = str(last_msg)
    
    prompt = (
        "Classify the following user input into exactly one category:\n"
        "- 'ops': Questions about e-commerce metrics, abandoned carts, revenue, orders, or operations.\n"
        "- 'chat': Greetings, pleasantries, or small talk (e.g., 'hi', 'hello', 'who are you').\n"
        "- 'off_topic': Anything completely unrelated to business or greetings (e.g., recipes, sports, jokes, code generation).\n\n"
        f"User input: {user_text}"
    )
    
    result = router_llm.invoke([HumanMessage(content=prompt)])
    return {"intent": result.intent}


def route_decision(state: AgentState) -> str:
    """Conditional router mapping."""
    return state.get("intent", "ops")


def fast_chat_node(state: AgentState) -> dict:
    """Handles simple greetings fast without tools."""
    msg = AIMessage(content="Hello! I am your Autonomous E-Commerce Operations Analyst. How can I help you analyze order performance or cart abandonment today?")
    return {"messages": [msg]}


def guardrail_node(state: AgentState) -> dict:
    """Refuses out-of-scope requests politely."""
    msg = AIMessage(content="I am an operational e-commerce analyst assistant. I can only assist with e-commerce store metrics, order summaries, and revenue analysis. Please let me know how I can help with store operations!")
    return {"messages": [msg]}


def ecom_analyst_node(state: AgentState) -> dict:
    """Main analyst node for operational queries."""
    system_prompt = SystemMessage(
        content=(
            "You are an Autonomous E-Commerce Operations Analyst. "
            "Your objective is to optimize online storefront performance, analyze order health, and reduce cart abandonment. "
            "Always use your available tools to query real database analytics and compute financial impacts before giving recommendations. "
            "When the user asks to send an email or perform an action, invoke the corresponding tool directly. Do not ask for confirmation in text—the system will handle approval automatically."
        )
    )
    messages = [system_prompt] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# Separate Tool Nodes
read_tools_node = ToolNode(tools=read_tools)
action_tools_node = ToolNode(tools=action_tools)


def route_tools(state: AgentState) -> Literal["read_tools", "action_tools", "__end__"]:
    """Determines whether to execute read tools, interrupt for action tools, or finish."""
    messages = state["messages"]
    last_message = messages[-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END

    called_tool_names = [tc["name"] for tc in last_message.tool_calls]
    action_tool_names = [t.name for t in action_tools]

    # If any action tool is requested, route to action_tools
    for name in called_tool_names:
        if name in action_tool_names:
            return "action_tools"

    return "read_tools"


# --- Graph Assembly ---

builder = StateGraph(AgentState)

builder.add_node("router", router_node)
builder.add_node("fast_chat", fast_chat_node)
builder.add_node("guardrail", guardrail_node)
builder.add_node("ecom_analyst", ecom_analyst_node)
builder.add_node("read_tools", read_tools_node)
builder.add_node("action_tools", action_tools_node)

# Entry point and initial intent router
builder.set_entry_point("router")

builder.add_conditional_edges(
    "router",
    route_decision,
    {
        "chat": "fast_chat",
        "off_topic": "guardrail",
        "ops": "ecom_analyst"
    }
)

builder.add_edge("fast_chat", END)
builder.add_edge("guardrail", END)

# Route from ecom_analyst dynamically based on tool calls
builder.add_conditional_edges(
    "ecom_analyst",
    route_tools,
    {
        "read_tools": "read_tools",
        "action_tools": "action_tools",
        END: END
    }
)

# Loop back to ecom_analyst after tool executions
builder.add_edge("read_tools", "ecom_analyst")
builder.add_edge("action_tools", "ecom_analyst")

memory = MemorySaver()

# Guard ONLY action_tools with the pause interrupt
graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["action_tools"]
)