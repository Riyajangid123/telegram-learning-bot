from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

class LLM:
    def llm(self):
        model=ChatGroq(model="llama-3.3-70b-versatile",temperature=0)
        return model