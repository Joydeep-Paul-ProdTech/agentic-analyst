import os
from typing import TypedDict, Annotated, Sequence
import operator
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

# Load environment variables (.env)
load_dotenv()

# ==========================================
# 1. E-COMMERCE DOMAIN TOOLS
# ==========================================

@tool
def query_order_analytics(category: str) -> str:
    """Queries e-commerce platform analytics for a specific product category (e.g., 'Apparel', 'Electronics')."""
    mock_ecommerce_db = {
        "ELECTRONICS": {
            "daily_orders": 1250,
            "cart_abandonment_rate": "68%",
            "return_rate": "14%",
            "top_friction_point": "Payment gateway timeout on checkout step 2"
        },
        "APPAREL": {
            "daily_orders": 3400,
            "cart_abandonment_rate": "42%",
            "return_rate": "28%",
            "top_friction_point": "Sizing chart ambiguity leading to high return volume"
        }
    }
    
    data = mock_ecommerce_db.get(category.upper())
    if data:
        return (f"Category: {category.upper()} | Daily Orders: {data['daily_orders']} | "
                f"Cart Abandonment: {data['cart_abandonment_rate']} | Return Rate: {data['return_rate']} | "
                f"Primary Bottleneck: {data['top_friction_point']}")
    return f"No analytics found for category '{category}' in the e-commerce database."

@tool
def calculate_revenue_impact(abandoned_carts: int, avg_order_value: float) -> str:
    """Calculates potential lost revenue from abandoned checkout carts based on Average Order Value (AOV)."""
    try:
        lost_revenue = abandoned_carts * avg_order_value
        return f"Estimated Lost Revenue: ${lost_revenue:,.2f} based on {abandoned_carts} orders at AOV of ${avg_order_value:.2f}"
    except Exception as e:
        return f"Error performing calculation: {str(e)}"

# Collect E-commerce tools list
tools = [query_order_analytics, calculate_revenue_impact]

# ==========================================
# 2. STATE SCHEMA & LLM INITIALIZATION
# ==========================================

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2
)
llm_with_tools = llm.bind_tools(tools)

# ==========================================
# 3. DEFINE GRAPH NODES
# ==========================================

def ecom_analyst_node(state: AgentState) -> dict:
    """E-commerce operational analyst node."""
    print("\n--- [NODE: E-COMMERCE ANALYST AGENT] ---")
    system_prompt = SystemMessage(
        content=(
            "You are an Autonomous E-Commerce Operations Analyst. "
            "Your objective is to optimize online storefront performance, reduce cart abandonment, and analyze return rates. "
            "Always use your available tools to pull real analytics data and compute financial impacts before giving recommendations."
        )
    )
    messages = [system_prompt] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}

tool_node = ToolNode(tools=tools)

# ==========================================
# 4. BUILD STATEGRAPH
# ==========================================

builder = StateGraph(AgentState)

builder.add_node("ecom_analyst", ecom_analyst_node)
builder.add_node("tools", tool_node)

builder.set_entry_point("ecom_analyst")

builder.add_conditional_edges(
    "ecom_analyst",
    tools_condition,
)

builder.add_edge("tools", "ecom_analyst")

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

# ==========================================
# 5. EXECUTION & TESTING
# ==========================================

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "ecom-session-1"}}
    
    print("Starting Autonomous E-Commerce Operations Agent...")
    
    ecom_query = (
        "Check store analytics for the Electronics category. "
        "If cart abandonment is high, estimate lost daily revenue assuming 850 abandoned orders at an average order value (AOV) of $120."
    )
    
    input_payload = {"messages": [HumanMessage(content=ecom_query)]}
    
    print(f"\nUser Query: {ecom_query}\n" + "-"*60)
    
    for event in graph.stream(input_payload, config=config, stream_mode="values"):
        latest_msg = event["messages"][-1]
        
        if hasattr(latest_msg, "tool_calls") and latest_msg.tool_calls:
            for tc in latest_msg.tool_calls:
                print(f"--> [TOOL CALL]: {tc['name']} with args: {tc['args']}")
        elif isinstance(latest_msg, ToolMessage):
            print(f"<-- [TOOL RESULT]: {latest_msg.content}")

    print("\n================ FINAL E-COMMERCE INSIGHTS ================")
    final_msg = graph.get_state(config).values["messages"][-1]
    
    # Handle Gemini structured text block vs simple string output
    if isinstance(final_msg.content, list):
        print(final_msg.content[0]["text"])
    else:
        print(final_msg.content)
    print("==========================================================")