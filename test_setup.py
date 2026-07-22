import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env
load_dotenv()

def main():
    print("Testing API connections...")
    
    # Initialize the Gemini model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0
    )
    
    # Invoke the model
    response = llm.invoke("Hello! Confirm that you are operational for the Autonomous Enterprise Operations Analyst project.")
    
    print("\n--- Model Response ---")
    print(response.content)
    print("----------------------\n")
    print("Check your LangSmith dashboard (https://smith.langchain.com/) under project 'agentic-analyst' to view this trace!")

if __name__ == "__main__":
    main()