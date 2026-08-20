from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()


class LLM:

    def llm(self, json_mode: bool = False):

        kwargs = {}

        if json_mode:
            kwargs["model_kwargs"] = {
                "response_format": {
                    "type": "json_object"
                }
            }

        model = ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            **kwargs
        )

        return model