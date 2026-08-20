from langchain_core.prompts import ChatPromptTemplate

from schema.schema import ResourcePlans
from agents.llm import LLM
from graph.state import LearningState
from database.queries import save_resources

import time
import os
import re
import json

from tavily import TavilyClient

tavily_client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


def clean_url(url: str) -> str:

    """Convert Markdown URL:
        [Example](https://example.com)
         ->
        https://example.com"""
    

    if not url:
        return ""

    url = url.strip()

    match = re.match(
        r"\[.*?\]\((https?://[^)]+)\)",
        url
    )

    if match:
        return match.group(1)

    return url


def _safe_tavily_search(
    query: str,
    max_results: int = 2
):

    try:

        response = tavily_client.search(
            query=query,
            max_results=max_results
        )

        results = []

        for result in response.get("results", []):

            title = result.get("title", "")
            url = clean_url(
                result.get("url", "")
            )

            if not url:
                continue

            results.append(
                {
                    "title": title,
                    "url": url
                }
            )

        return results

    except Exception as e:

        print(
            f"Tavily search failed for "
            f"'{query}': {e}"
        )

        return []


def search_articles(query: str):

    return _safe_tavily_search(
        query
    )


def youtube_search(query: str):

    return _safe_tavily_search(
        f"{query} tutorial site:youtube.com"
    )


def search_courses(query: str):

    return _safe_tavily_search(
        f"{query} free course "
        f"site:coursera.org OR site:freecodecamp.org"
    )


class ResourceFinderAgent:

    def __init__(self):

        self.llm = LLM().llm()

        self.prompt = ChatPromptTemplate.from_template(
            """
You are an AI Resource Organizer.

Your task is to organize verified learning resources
for every topic in the curriculum.

Curriculum:
{curriculum}

Verified Search Results:
{search_results}


STRICT RULES:

1. Every topic from the curriculum MUST appear exactly once.

2. Keep the topics in the same order as the curriculum.

3. ONLY use URLs that exist in the Verified Search Results.

4. NEVER invent a URL.

5. NEVER modify a URL.

6. Use the exact title from the Verified Search Results.

7. Every resource must contain ONLY:
   - title
   - url

8. If there are no articles for a topic:
   "articles": []

9. If there are no YouTube videos for a topic:
   "youtube_videos": []

10. If there are no courses for a topic:
    "courses": []

11. URLs must be plain URLs.

12. NEVER use Markdown links.

    Correct:
    "url": "https://example.com"

    Incorrect:
    "url": "[https://example.com](https://example.com)"

13. Do not create additional fields.

14. Do not remove required fields.

15. Return data matching the ResourcePlans schema.

16. Do NOT return a raw JSON array.

17. Do NOT provide explanations.

Return ONLY the structured ResourcePlans object.
"""
        )

        self.chain = (
            self.prompt
            | self.llm.with_structured_output(
                ResourcePlans,
                method="function_calling"
            )
        )


    def resource_finder_agent(
        self,
        state: LearningState
    ):

        curriculum = state.get(
            "curriculum"
        )

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

            print(
                f"\nSearching resources for: "
                f"{topic.topic}"
            )

            try:

                time.sleep(1)

                articles = search_articles(
                    topic.topic
                )

                time.sleep(1.5)

                youtube = youtube_search(
                    topic.topic
                )

                time.sleep(1.5)

                courses = search_courses(
                    topic.topic
                )

                all_results.append(
                    {
                        "topic": topic.topic,
                        "difficulty": topic.difficulty,
                        "articles": articles,
                        "youtube_videos": youtube,
                        "courses": courses
                    }
                )

                print(
                    f"Search completed for: "
                    f"{topic.topic}"
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


        print(
            "\n========== SEARCH RESULTS =========="
        )

        print(
            json.dumps(
                all_results,
                indent=2,
                ensure_ascii=False
            )
        )


        print(
            "\nCalling Resource LLM..."
        )

        try:

            resource_plan = self.chain.invoke(
                {
                    "curriculum": json.dumps(
                        curriculum.model_dump(),
                        indent=2,
                        ensure_ascii=False
                    ),

                    "search_results": json.dumps(
                        all_results,
                        indent=2,
                        ensure_ascii=False
                    )
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

        print(
            "\nLLM returned successfully."
        )

        print(
            json.dumps(
                resource_plan.model_dump(),
                indent=2,
                ensure_ascii=False
            )
        )


        state["resources"] = resource_plan

        try:

            save_resources(
                curriculum_id=state["curriculum_id"],
                resources=resource_plan.model_dump()
            )

            print(
                "Resources saved successfully."
            )

        except Exception as e:

            print(
                f"Failed to save resources: {e}"
            )


        #telegram message

        msg = (
            "📚 <b>Learning Resources</b>\n\n"
        )


        for topic in resource_plan.resources:

            msg += (
                f"📌 <b>{topic.topic}</b>\n\n"
            )

            if topic.articles:

                msg += (
                    "📄 <b>Articles</b>\n"
                )

                for article in topic.articles:

                    msg += (
                        f"• <a href='{article.url}'>"
                        f"{article.title}"
                        f"</a>\n"
                    )


            if topic.youtube_videos:

                msg += (
                    "\n🎥 <b>YouTube</b>\n"
                )

                for video in topic.youtube_videos:

                    msg += (
                        f"• <a href='{video.url}'>"
                        f"{video.title}"
                        f"</a>\n"
                    )

            if topic.courses:

                msg += (
                    "\n🎓 <b>Courses</b>\n"
                )

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