from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()


class LLM:

    def llm(self):

        model = ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_kwargs={
                "response_format": {
                    "type": "json_object"
                }
            }
        )

        return model