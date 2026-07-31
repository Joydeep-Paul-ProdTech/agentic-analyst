import pandas as pd
import sqlite3
import streamlit as st
import uuid

# Import your compiled LangGraph workflow from agent.py
from agent import graph

# ------------------------------------------------------------------------------
# 1. Page Configuration & Layout Strategy
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Autonomous E-commerce Operations Analyst",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛍️ Autonomous E-commerce Operations Analyst")
st.caption("Real-time operational dashboard & AI assistant powered by Gemini 2.5 Flash & LangGraph.")

# ------------------------------------------------------------------------------
# 2. Session State Initialization
# ------------------------------------------------------------------------------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = False

# LangGraph thread configuration for stateful checkpointing
config = {"configurable": {"thread_id": st.session_state.thread_id}}

# ------------------------------------------------------------------------------
# Helper Function for Response Text Extraction
# ------------------------------------------------------------------------------
def extract_clean_content(msg):
    raw_content = getattr(msg, "content", str(msg)) if msg else "N/A"
    if isinstance(raw_content, list) and len(raw_content) > 0:
        first_item = raw_content[0]
        if isinstance(first_item, dict):
            return first_item.get("text", str(first_item))
        return str(first_item)
    return str(raw_content)

# ------------------------------------------------------------------------------
# 3. Sidebar - Session Information & System Status
# ------------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Session Controls")
    st.info(f"**Thread ID:** `{st.session_state.thread_id[:8]}...`")

    if st.button("🔄 Reset Conversation Thread", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.pending_approval = False
        st.rerun()

    st.markdown("---")
    st.subheader("🛡️ Safety & Safeguards")
    st.markdown("""
    * **Read Operations:** Executed automatically.
    * **Write/Action Operations:** Trigger a mandatory Human-In-The-Loop approval step before execution.
    """)

# ------------------------------------------------------------------------------
# 4. Top KPI Summary Dashboard
# ------------------------------------------------------------------------------
st.markdown("### 📊 Operational Overview")
col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

with col_kpi1:
    st.metric(label="Active Abandoned Carts", value="14", delta="+2 today")
with col_kpi2:
    st.metric(label="Recoverable Revenue", value="$2,450.00", delta="$350.00")
with col_kpi3:
    st.metric(label="Pending Action Tasks", value="1", delta="Requires Review", delta_color="off")
with col_kpi4:
    st.metric(label="Agent Status", value="Active / Pausable", delta="HITL Armed")

st.markdown("---")

# ------------------------------------------------------------------------------
# 5. Main Dashboard Tabs
# ------------------------------------------------------------------------------
tab_assistant, tab_analytics = st.tabs(["🤖 Operations Assistant", "📈 Analytics & Logs"])

# ==============================================================================
# TAB 1: Interactive Operations Console
# ==============================================================================
with tab_assistant:
    st.subheader("Interactive Operations Console")

    # Render previous conversation history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --------------------------------------------------------------------------
    # 6. HITL Intercept Handler (Render Action Approval UI if graph is paused)
    # --------------------------------------------------------------------------
    snapshot = graph.get_state(config)

    if snapshot.next:
        st.session_state.pending_approval = True
        pending_msg = snapshot.values["messages"][-1]
        tool_calls = getattr(pending_msg, "tool_calls", [])

        st.warning("⚠️ **Action Interrupted: Human Approval Required**")
        st.write("The assistant generated a write/action proposal that requires manual verification before execution.")

        for tool_call in tool_calls:
            with st.expander(f"⚙️ Pending Action Tool: `{tool_call.get('name')}`", expanded=True):
                st.json(tool_call.get("args"))

        btn_col1, btn_col2 = st.columns([1, 4])

        with btn_col1:
            if st.button("✅ Approve Action", type="primary", use_container_width=True, key="approve_action"):
                st.session_state.pending_approval = False

                with st.spinner("Executing approved action tool..."):
                    try:
                        # Resume execution by passing None to the interrupted graph thread
                        for event in graph.stream(None, config=config, stream_mode="values"):
                            pass

                        # Retrieve final response after tool execution
                        updated_snapshot = graph.get_state(config)
                        final_msg = updated_snapshot.values["messages"][-1]
                        response_text = extract_clean_content(final_msg)

                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                        st.success("Action executed successfully!")
                        st.rerun()
                    except Exception as e:
                        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                            st.error("⚠️ **API Quota Exceeded (429):** You hit the Gemini free-tier daily request limit. Please wait a few moments or switch your key/model.")
                        else:
                            st.error(f"Error resuming graph execution: {e}")

        with btn_col2:
            if st.button("❌ Reject Action", use_container_width=True, key="reject_action"):
                st.session_state.pending_approval = False
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "🚫 **Action Rejected:** Operator canceled the tool execution step."
                })
                st.warning("Action execution rejected by operator.")
                st.rerun()

    # --------------------------------------------------------------------------
    # 7. Chat Input Handling
    # --------------------------------------------------------------------------
    user_prompt = st.chat_input(
        "Request an action (e.g., 'Send a recovery email with 15% off to cart CART_101 for user USR_501 at user@example.com')...",
        disabled=st.session_state.pending_approval
    )

    if user_prompt and not st.session_state.pending_approval:
        # Append and display user input
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Stream execution through LangGraph
        with st.chat_message("assistant"):
            with st.spinner("Analyzing operational state..."):
                try:
                    events = graph.stream(
                        {"messages": [("user", user_prompt)]},
                        config=config,
                        stream_mode="values"
                    )
                    for event in events:
                        pass

                    # Check if execution completed or was paused by interrupt_before
                    updated_snapshot = graph.get_state(config)

                    if updated_snapshot.next:
                        st.session_state.pending_approval = True
                        st.rerun()
                    else:
                        final_msg = updated_snapshot.values["messages"][-1]
                        response_text = extract_clean_content(final_msg)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                        st.markdown(response_text)

                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                        st.error("⚠️ **API Quota Exceeded (429):** You hit the Gemini daily free-tier quota (20 requests/day). Please wait for quota refresh or update `agent.py` to use `gemini-1.5-flash`.")
                    else:
                        st.error(f"Execution Error: {e}")

# ==============================================================================
# TAB 2: Operational Analytics & System Logs
# ==============================================================================
with tab_analytics:
    st.subheader("📊 System Operational Metrics & Audit Trail")

    # --------------------------------------------------------------------------
    # Real-Time Database Metrics (With Safe Auto-Creation)
    # --------------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    try:
        conn = sqlite3.connect("ecommerce_ops.db")
        cursor = conn.cursor()

        # Ensure action_logs table exists so queries won't fail on a clean DB
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action_type TEXT,
                recipient TEXT,
                cart_id TEXT,
                status TEXT,
                details TEXT
            )
        """)
        conn.commit()

        # Fetch active count from abandoned_carts
        try:
            cursor.execute("SELECT COUNT(*) FROM abandoned_carts WHERE status = 'ABANDONED'")
            abandoned_count = cursor.fetchone()[0]

            cursor.execute("PRAGMA table_info(abandoned_carts)")
            cols = [col[1] for col in cursor.fetchall()]
            value_col = next((c for c in ['cart_value', 'total_amount', 'cart_total', 'amount', 'price'] if c in cols), None)

            if value_col:
                cursor.execute(f"SELECT IFNULL(SUM({value_col}), 0) FROM abandoned_carts WHERE status = 'ABANDONED'")
                total_value = cursor.fetchone()[0]
            else:
                total_value = 0.0
        except Exception:
            abandoned_count = 0
            total_value = 0.0

        # Fetch metrics from action_logs
        cursor.execute("SELECT COUNT(*) FROM action_logs WHERE status = 'SUCCESS'")
        emails_sent = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM action_logs WHERE status = 'REJECTED'")
        actions_rejected = cursor.fetchone()[0]

        conn.close()

        col1.metric("Active Abandoned Carts", abandoned_count)
        col2.metric("Recoverable Revenue", f"${total_value:,.2f}")
        col3.metric("Emails Dispatched", emails_sent)
        col4.metric("Actions Intercepted/Rejected", actions_rejected)

    except Exception as e:
        st.warning(f"Database metrics currently offline: {e}")

    st.divider()

    # --------------------------------------------------------------------------
    # LangGraph State History (Checkpoint Trail)
    # --------------------------------------------------------------------------
    st.subheader("🔄 Thread State History & Checkpoints")

    state_history_data = []

    try:
        for state_snapshot in graph.get_state_history(config):
            step_next = state_snapshot.next
            checkpoint_id = state_snapshot.config["configurable"].get("checkpoint_id", "N/A")
            messages = state_snapshot.values.get("messages", [])
            
            last_msg = messages[-1] if messages else None
            msg_type = type(last_msg).__name__ if last_msg else "N/A"
            msg_content = extract_clean_content(last_msg)

            if len(msg_content) > 60:
                msg_content = msg_content[:60] + "..."

            state_history_data.append({
                "Checkpoint ID": str(checkpoint_id)[:8] + "...",
                "Next Node": ", ".join(step_next) if step_next else "END",
                "Last Message Type": str(msg_type),
                "Content Snippet": str(msg_content),
                "Tasks Pending": len(state_snapshot.tasks)
            })

        if state_history_data:
            df_state = pd.DataFrame(state_history_data)
            st.dataframe(
                df_state,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No checkpoint history found for the current thread.")

    except Exception as e:
        st.error(f"Failed to retrieve state history: {e}")

    st.divider()

    # --------------------------------------------------------------------------
    # Action Execution Audit Logs
    # --------------------------------------------------------------------------
    st.subheader("📜 Action Execution & Interception Logs")

    try:
        conn = sqlite3.connect("ecommerce_ops.db")
        logs_df = pd.read_sql_query(
            "SELECT timestamp, action_type, recipient, cart_id, status, details FROM action_logs ORDER BY timestamp DESC", 
            conn
        )
        conn.close()

        if not logs_df.empty:
            st.dataframe(
                logs_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "timestamp": "Timestamp",
                    "action_type": "Action",
                    "recipient": "Target Recipient",
                    "cart_id": "Cart ID",
                    "status": st.column_config.StatusColumn("Status"),
                    "details": "Execution Details"
                }
            )
        else:
            st.info("No tool execution logs recorded yet.")

    except Exception:
        st.info("No tool execution logs recorded yet.")