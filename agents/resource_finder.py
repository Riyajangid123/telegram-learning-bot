
from langchain_core.prompts import ChatPromptTemplate

from schema.schema import ResourcePlan
from agents.llm import LLM
from graph.state import LearningState

from database.queries import save_resources

import time
import os
from tavily import TavilyClient

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def _safe_tavily_search(query: str, max_results: int = 2):
    try:
        response = tavily_client.search(query, max_results=max_results)
        return [
            {"title": r["title"], "url": r["url"]}
            for r in response.get("results", [])
        ]
    except Exception as e:
        print(f"Tavily search failed for '{query}': {e}")
        return []

def search_articles(query: str):
    return _safe_tavily_search(query)

def youtube_search(query: str):
    return _safe_tavily_search(f"{query} tutorial site:youtube.com")

def search_courses(query: str):
    return _safe_tavily_search(f"{query} free course site:coursera.org OR site:freecodecamp.org")


class ResourceFinderAgent:

    def __init__(self):

        self.llm = LLM().llm()

        self.prompt = ChatPromptTemplate.from_template("""
        You are an AI Resource Organizer.

        Curriculum:
        {curriculum}

        Verified Search Results:
        {search_results}

        Create a ResourcePlan.

        STRICT RULES:

        1. ONLY use URLs present in Verified Search Results.
        2. NEVER invent a title.
        3. NEVER invent a URL.
        4. If a topic has no articles, return articles=[].
        5. If a topic has no YouTube videos, return youtube_videos=[].
        6. If a topic has no courses, return courses=[].
        7. Every topic from the curriculum MUST appear exactly once.
        8. Return ONLY the ResourcePlan object.

        Return only data matching the provided structured output schema.
        Do not output Python code.
        Do not output the Pydantic class.
        Do not provide explanations outside the structured result.
        """)

        self.chain = (
            self.prompt
            | self.llm.with_structured_output(ResourcePlan,method="json_schema")
        )

    def resource_finder_agent(self, state: LearningState):

        curriculum = state["curriculum"]

        if curriculum is None:

            state["response_message"] = (
                    "🤔 <b>Hold on!</b>\n\n"
                    "I don't have your curriculum planner results yet, so I can't "
                    "provide resources.\n\n"
                    "📝 Please complete the skill assessment questions first — "
                    "your answers help me tailor everything to your actual level.\n\n"
                    "Type <b>/start</b> to begin your assessment. 🚀"
                )

            return state

        all_results = []

        for topic in curriculum.learning_path:

            print(f"Searching resources for {topic.topic}")
            
            time.sleep(1)

            
            articles = search_articles(topic.topic)
            time.sleep(1.5)
            youtube = youtube_search(topic.topic)
            time.sleep(1.5)
            courses = search_courses(topic.topic)
            time.sleep(1.5)
            print("Search completed")

            all_results.append({

                "topic": topic.topic,

                "difficulty": topic.difficulty,

                "articles": articles,

                "youtube": youtube,

                "courses": courses

            })

            print(all_results)

        print("Calling LLM...")

        resource_plan = self.chain.invoke({

            "curriculum": curriculum,

            "search_results": all_results

        })

        print("LLM returned")
        print(resource_plan)

        state["resources"] = resource_plan

        save_resources(

            curriculum_id=state["curriculum_id"],

            resources=resource_plan.model_dump()

        )

        print("Saved")

        msg = "📚 <b>Learning Resources</b>\n\n"

        for topic in resource_plan.resources:
            msg += f"📌 <b>{topic.topic}</b>\n\n"

            if topic.articles:

                msg += "📄 <b>Articles</b>\n"

                for a in topic.articles:

                    msg += (
                        f"• <a href='{a.url}'>{a.title}</a>\n"
                    )

            if topic.youtube_videos:

                msg += "\n🎥 <b>YouTube</b>\n"

                for y in topic.youtube_videos:

                    msg += (
                            f"• <a href='{y.url}'>{y.title}</a>\n"
                    )

            if topic.courses:

                msg += "\n🎓 <b>Courses</b>\n"

                for c in topic.courses:

                    msg += (
                            f"• <a href='{c.url}'>{c.title}</a>\n"
                    )

            msg += "\n"

        msg += (
                "\n━━━━━━━━━━━━━━━━━━\n\n"
                "✅ These resources are organized in the same order as your roadmap.\n\n"
                "Study each topic one by one.\n\n"
                "When you're ready, type <b>/quiz</b> to test your knowledge."
            )

        state["response_message"] = msg

        state["phase"] = "learning"

        return state