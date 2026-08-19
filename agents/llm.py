from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()


class LLM:

    def llm(self):

        model = ChatGroq(
            model="qwen/qwen3.6-27b",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )

        return model