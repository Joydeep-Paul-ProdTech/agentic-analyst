# 🤖 Autonomous E-commerce Operations Analyst

An agentic AI system built to automate e-commerce operational workflows. The system intelligently routes queries between standard data analysis and action-oriented operational tasks, enforcing strict **Human-in-the-Loop (HITL)** guardrails before executing high-impact actions (like sending customer recovery emails or logging database updates).

---

## 🌟 Key Features

* **Stateful Orchestration:** Built with **LangGraph** to manage multi-turn conversational state, decision routing, and execution interrupts.
* **Human-in-the-Loop (HITL) Guardrails:** Uses `interrupt_before` logic on sensitive tools to pause execution until a human operator approves or rejects the action via the UI.
* **Dual Action Tools:**
  * **Automated Email Dispatch:** Sends customer retention emails via `smtplib` upon operator authorization.
  * **Audit Logging & Analytics:** Automatically logs all executed recovery actions into an `ecommerce_ops.db` SQLite database and syncs directly with the UI.
* **Interactive Dashboard:** Powered by **Streamlit** for real-time chat interactions, execution approval cards, and audit log visualizers.

---

## 🏗️ Architecture & Execution Flow

```text
[ User Prompt ] 
       │
       ▼
[ LangGraph Router Node ] 
       ├── (Read Query) ──► [ LLM Knowledge Response ] ──► [ Streamlit UI ]
       │
       └── (Action Needed) ──► [ HITL Interrupt Pause ] 
                                      │
                                [ Human Operator ]
                                ├── (Approve) ──► [ Execute Tools: Email + DB Log ] ──► [ Streamlit UI ]
                                └── (Reject)  ──► [ Abort Execution & Reset ]

## 🛠️ Tech Stack
Framework: Python, LangGraph, LangChain

LLM Engine: Google Gemini API (gemini-2.5-flash / gemini-pro)

Frontend UI: Streamlit

Database & Persistence: SQLite3

Protocols & Utilities: smtplib (SMTP Email), python-dotenv\

## 🚀 Quickstart Guide
1. Prerequisites
Ensure you have Python 3.10+ installed.

2. Installation & Setup

# Clone the repository
git clone [https://github.com/Joydeep-Paul-ProdTech/agentic-analyst.git](https://github.com/Joydeep-Paul-ProdTech/agentic-analyst.git)
cd agentic-analyst

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

3. Environment Variables
Create a .env file in the root directory based on .env.example:

GEMINI_API_KEY=your_gemini_api_key
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password

## 📌 Demo & Proof of Work
Ref Link : TBD
