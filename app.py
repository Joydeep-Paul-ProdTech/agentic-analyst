import streamlit as st
import pandas as pd
import numpy as np
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agent import graph

# Page Configuration
st.set_page_config(
    page_title="Autonomous E-Commerce Ops Analyst",
    page_icon="🛍️",
    layout="wide"
)

# Header Section
st.title("🛍️ Autonomous E-Commerce Operations Analyst")
st.caption("Powered by LangGraph & Google Gemini 2.5 Flash")

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "ecom-session-1"

# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Session Controls")
    st.write(f"**Thread ID:** `{st.session_state.thread_id}`")
    st.divider()
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Top KPI Metric Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Cart Abandonment Rate", value="30.0%", delta="-2.5% vs last week")
with col2:
    st.metric(label="Est. Revenue Loss", value="$12,750", delta="+$1,200", delta_color="inverse")
with col3:
    st.metric(label="Abandoned Carts", value="150", delta="10 vs yesterday")
with col4:
    st.metric(label="Avg Order Value (AOV)", value="$85.00", delta="+$2.50")

st.divider()

# Navigation Tabs
tab_chat, tab_analytics = st.tabs(["💬 Interactive AI Agent", "📊 Visual Analytics"])

# ==================== TAB 1: AI AGENT CHAT ====================
with tab_chat:
    # Display Chat History
    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.write(message.content)
        elif isinstance(message, AIMessage) and message.content:
            content = message.content[0]["text"] if isinstance(message.content, list) else message.content
            with st.chat_message("assistant"):
                st.markdown(content)

    # Chat Input
    if user_input := st.chat_input("Ask about store analytics, cart abandonment, or revenue impact..."):
        user_msg = HumanMessage(content=user_input)
        st.session_state.messages.append(user_msg)
        
        with st.chat_message("user"):
            st.write(user_input)

        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        
        with st.chat_message("assistant"):
            with st.status("Agent thinking & invoking tools...", expanded=True) as status:
                final_response_text = ""
                
                for event in graph.stream({"messages": [user_msg]}, config=config, stream_mode="values"):
                    latest_msg = event["messages"][-1]
                    
                    if hasattr(latest_msg, "tool_calls") and latest_msg.tool_calls:
                        for tc in latest_msg.tool_calls:
                            st.write(f"🔧 **Tool Call:** `{tc['name']}`")
                            st.json(tc['args'])
                    elif isinstance(latest_msg, ToolMessage):
                        st.write(f"📊 **Tool Result:**")
                        st.info(latest_msg.content)
                    elif isinstance(latest_msg, AIMessage) and latest_msg.content:
                        final_response_text = latest_msg.content[0]["text"] if isinstance(latest_msg.content, list) else latest_msg.content

                status.update(label="Analysis complete!", state="complete", expanded=False)
                
            st.markdown(final_response_text)
            st.session_state.messages.append(AIMessage(content=final_response_text))

# ==================== TAB 2: VISUAL ANALYTICS ====================
with tab_analytics:
    st.subheader("📈 Cart Abandonment Trends")
    
    # Generate Sample Trend Data
    chart_data = pd.DataFrame(
        np.random.randn(20, 2) / [20, 20] + [0.30, 85],
        columns=["Abandonment Rate (%)", "Avg Order Value ($)"]
    )
    st.line_chart(chart_data)
    
    st.subheader("🛒 Breakdown by Category")
    category_data = pd.DataFrame({
        "Category": ["Electronics", "Apparel", "Home & Kitchen", "Beauty"],
        "Abandoned Carts": [65, 45, 25, 15]
    })
    st.bar_chart(category_data, x="Category", y="Abandoned Carts")