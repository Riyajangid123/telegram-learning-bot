from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()


class LLM:

    def llm(self):

        model = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )

        return model