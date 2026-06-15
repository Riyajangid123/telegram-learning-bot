from database.queries import insert_resources, get_curriculum_by_user, get_user_by_telegram_id
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from duckduckgo_search import DDGS
import json
import os
import time
from graph.state import LearningState
from dotenv import load_dotenv

load_dotenv()


@tool
def search_articles(query: str) -> str:
    """Search for articles and documentation on a topic"""
    try:
        time.sleep(2)
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2))
        if not results:
            return "No results found"
        output = []
        for r in results:
            output.append(f"Title: {r['title']}\nURL: {r['href']}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Search unavailable: {str(e)}"


@tool
def youtube_search(query: str) -> str:
    """Search for YouTube tutorial videos on a topic"""
    try:
        time.sleep(2)
        with DDGS() as ddgs:
            results = list(ddgs.videos(
                f"{query} tutorial", max_results=2
            ))
        if not results:
            return "No videos found"
        output = []
        for r in results:
            output.append(f"Title: {r['title']}\nURL: {r['content']}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Search unavailable: {str(e)}"


@tool
def search_courses(query: str) -> str:
    """Search for free online courses on a topic"""
    try:
        time.sleep(2)
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f"{query} free course site:coursera.org OR site:freecodecamp.org",
                max_results=2
            ))
        if not results:
            return "No courses found"
        output = []
        for r in results:
            output.append(f"Title: {r['title']}\nURL: {r['href']}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Search unavailable: {str(e)}"


tools = [search_articles, youtube_search, search_courses]
tool_node = ToolNode(tools) 


def resource_finder_agent(state: LearningState):
    telegram_id = state["telegram_id"]
    curriculum = state.get("curriculum", [])
    topic = state.get("topic", "")
    skill_level = state.get("skill_level", "beginner")
    messages = state.get("messages", [])

    model = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.3,
        api_key=os.getenv("GROQ_API_KEY")
    )

    model_with_tools = model.bind_tools(tools)

    if not messages:
        system_prompt = f"""You are a learning resource finder.
        Find resources for each week of this curriculum:
        Topic: {topic}
        Skill Level: {skill_level}
        Curriculum: {str(curriculum)}

        Use the available tools to search for:
        - youtube_search: find tutorial videos
        - search_articles: find documentation
        - search_courses: find free courses

        Search for Week 1 first, then Week 2, etc.
        After all searches, return resources as JSON:
        {{
            "week_1": [
                {{"title": "...", "url": "...", "type": "youtube"}},
                {{"title": "...", "url": "...", "type": "article"}}
            ],
            "week_2": [...]
        }}"""
        messages = [HumanMessage(content=system_prompt)]

    
    response = model_with_tools.invoke(messages)


    if response.tool_calls:
        print(f"🔧 Tool called: {[t['name'] for t in response.tool_calls]}")
        return {"messages": messages + [response]}


    print("✅ Resource finder complete")
    final_text = response.content


    try:
        clean = final_text.strip()
        clean = clean.replace("```json", "").replace("```", "").strip()
        resources_per_week = json.loads(clean)
    except Exception as e:
        print(f"❌ Resource parsing error: {str(e)}")
        resources_per_week = {
            f"week_{w['week']}": [] for w in curriculum
        }


    user = get_user_by_telegram_id(telegram_id)
    user_id = user["id"]
    db_curriculum = get_curriculum_by_user(user_id)

    for week in db_curriculum:
        week_key = f"week_{week['week_number']}"
        resources = resources_per_week.get(week_key, [])
        if resources:
            insert_resources(
                curriculum_id=week["id"],
                resources=resources
            )

    message_lines = [f"🔍 Resources for {topic}:\n"]
    for week in curriculum:
        week_key = f"week_{week['week']}"
        week_resources = resources_per_week.get(week_key, [])
        message_lines.append(f"📅 Week {week['week']}: {week['title']}")
        for r in week_resources:
            icon = "🎥" if r["type"] == "youtube" else "📖" if r["type"] == "article" else "🎓"
            message_lines.append(f"  {icon} {r['title']}: {r['url']}")
        message_lines.append("")

    response_message = "\n".join(message_lines)

    return {
        "resources": resources_per_week,
        "response_message": response_message,
        "messages": messages + [response]
    }