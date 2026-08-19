from langchain_core.prompts import ChatPromptTemplate

from schema.schema import ResourcePlans
from agents.llm import LLM
from graph.state import LearningState

from database.queries import save_resources

import time
import os
from tavily import TavilyClient


tavily_client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


def _safe_tavily_search(query: str, max_results: int = 2):
    try:
        response = tavily_client.search(
            query=query,
            max_results=max_results
        )

        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", "")
            }
            for r in response.get("results", [])
        ]

    except Exception as e:
        print(f"Tavily search failed for '{query}': {e}")
        return []


def search_articles(query: str):
    return _safe_tavily_search(query)


def youtube_search(query: str):
    return _safe_tavily_search(
        f"{query} tutorial site:youtube.com"
    )


def search_courses(query: str):
    return _safe_tavily_search(
        f"{query} free course site:coursera.org OR site:freecodecamp.org"
    )


class ResourceFinderAgent:

    def __init__(self):

        self.llm = LLM().llm()

        self.prompt = ChatPromptTemplate.from_template("""
You are an AI Resource Organizer.

Your task is to organize verified learning resources for every
topic in the curriculum.

Curriculum:
{curriculum}

Verified Search Results:
{search_results}

STRICT RULES:

1. Every topic from the curriculum MUST appear exactly once.

2. Use ONLY URLs that exist in Verified Search Results.

3. NEVER invent URLs.

4. NEVER modify URLs.

5. Use the exact title from the Verified Search Results.

6. If no articles are available for a topic, return:
   "articles": []

7. If no YouTube videos are available for a topic, return:
   "youtube_videos": []

8. If no courses are available for a topic, return:
   "courses": []

9. Keep resources organized according to the curriculum order.

10. The final response MUST be a JSON OBJECT matching the
    ResourcePlans schema.

11. Do NOT return a raw JSON array.

12. Do NOT wrap URLs in Markdown.
    Example:
    "url": "https://example.com"

13. Do not provide explanations outside the structured result.

Return ONLY the structured ResourcePlans object.
""")

        self.chain = (
            self.prompt
            | self.llm.with_structured_output(
                ResourcePlans,
                method="json_schema"
            )
        )

    def resource_finder_agent(self, state: LearningState):

        curriculum = state.get("curriculum")

        if curriculum is None:

            state["response_message"] = (
                "🤔 <b>Hold on!</b>\n\n"
                "I don't have your curriculum planner results yet, "
                "so I can't provide resources.\n\n"
                "📝 Please complete the skill assessment questions "
                "first — your answers help me tailor everything "
                "to your actual level.\n\n"
                "Type <b>/start</b> to begin your assessment. 🚀"
            )

            return state

        all_results = []

        for topic in curriculum.learning_path:

            print(f"Searching resources for: {topic.topic}")

            try:

                time.sleep(1)

                articles = search_articles(topic.topic)

                time.sleep(1.5)

                youtube = youtube_search(topic.topic)

                time.sleep(1.5)

                courses = search_courses(topic.topic)

                time.sleep(1.5)

                print(f"Search completed for: {topic.topic}")

                all_results.append(
                    {
                        "topic": topic.topic,
                        "difficulty": topic.difficulty,
                        "articles": articles,
                        "youtube_videos": youtube,
                        "courses": courses
                    }
                )

            except Exception as e:

                print(
                    f"Resource search failed for "
                    f"{topic.topic}: {e}"
                )

                all_results.append(
                    {
                        "topic": topic.topic,
                        "difficulty": topic.difficulty,
                        "articles": [],
                        "youtube_videos": [],
                        "courses": []
                    }
                )

        print("\n========== SEARCH RESULTS ==========")
        print(all_results)


        print("\nCalling Resource LLM...")

        try:

            resource_plan = self.chain.invoke(
                {
                    "curriculum": curriculum.model_dump(),
                    "search_results": all_results
                }
            )

        except Exception as e:

            print(
                f"Resource plan generation failed: {e}"
            )

            state["response_message"] = (
                "❌ <b>Resource generation failed.</b>\n\n"
                "I couldn't organize the learning resources "
                "right now. Please try again."
            )

            return state

        print("LLM returned")

        print(
            resource_plan.model_dump()
        )


        state["resources"] = resource_plan

        save_resources(
            curriculum_id=state["curriculum_id"],
            resources=resource_plan.model_dump()
        )

        print("Resources saved successfully")

        # Telegram message

        msg = "📚 <b>Learning Resources</b>\n\n"

        for topic in resource_plan.resources:

            msg += (
                f"📌 <b>{topic.topic}</b>\n\n"
            )

            if topic.articles:

                msg += "📄 <b>Articles</b>\n"

                for article in topic.articles:

                    msg += (
                        f"• <a href='{article.url}'>"
                        f"{article.title}"
                        f"</a>\n"
                    )

            if topic.youtube_videos:

                msg += "\n🎥 <b>YouTube</b>\n"

                for video in topic.youtube_videos:

                    msg += (
                        f"• <a href='{video.url}'>"
                        f"{video.title}"
                        f"</a>\n"
                    )

            if topic.courses:

                msg += "\n🎓 <b>Courses</b>\n"

                for course in topic.courses:

                    msg += (
                        f"• <a href='{course.url}'>"
                        f"{course.title}"
                        f"</a>\n"
                    )

            msg += "\n"

        msg += (
            "━━━━━━━━━━━━━━━━━━\n\n"
            "✅ These resources are organized in the "
            "same order as your roadmap.\n\n"
            "Study each topic one by one.\n\n"
            "When you're ready, type <b>/quiz</b> "
            "to test your knowledge."
        )

        state["response_message"] = msg

        state["phase"] = "learning"

        return state