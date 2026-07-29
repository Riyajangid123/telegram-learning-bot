from ddgs import DDGS
from langchain_core.prompts import ChatPromptTemplate

from schema.schema import ResourcePlan
from agents.llm import LLM
from graph.state import LearningState

from database.queries import save_resources

import time

import time
from ddgs.exceptions import RatelimitException

def _safe_search(fn, *args, retries=2, delay=3, **kwargs):
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except RatelimitException:
            if attempt < retries:
                time.sleep(delay * (attempt + 1))  
            else:
                return []  
            
def search_articles(query: str):
    def _do():
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2))
        return [{"title": r["title"], "url": r["href"]} for r in results]
    return _safe_search(_do)

def youtube_search(query: str):
    def _do():
        with DDGS() as ddgs:
            results = list(ddgs.videos(f"{query} tutorial", max_results=2))
        return [{"title": r["title"], "url": r["content"]} for r in results]
    return _safe_search(_do)

def search_courses(query: str):
    def _do():
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f"{query} free course site:coursera.org OR site:freecodecamp.org",
                max_results=2
            ))
        return [{"title": r["title"], "url": r["href"]} for r in results]
    return _safe_search(_do)


class ResourceFinderAgent:

    def __init__(self):

        self.llm = LLM().llm()

        self.prompt = ChatPromptTemplate.from_template("""
        You are an AI Resource Organizer.

        Curriculum:
        {curriculum}

        Search Results:
        {search_results}

        Convert these search results into the ResourcePlan schema.

        Rules:

        - Do not invent URLs.
        - Keep only high quality resources.
        - Group resources by topic.
        - Return ONLY the ResourcePlan schema.
        """)

        self.chain = (
            self.prompt
            | self.llm.with_structured_output(ResourcePlan)
        )

    def resource_finder_agent(self, state: LearningState):

        curriculum = state["curriculum"]

        if curriculum is None:

            state["response_message"] = (
                    "Curriculum not found."
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

            all_results.append({

                "topic": topic.topic,

                "difficulty": topic.difficulty,

                "articles": articles,

                "youtube": youtube,

                "courses": courses

            })

        resource_plan = self.chain.invoke({

            "curriculum": curriculum.model_dump(),

            "search_results": all_results

        })

        state["resources"] = resource_plan

        save_resources(

            curriculum_id=state["curriculum_id"],

            resources=resource_plan.model_dump()

        )

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