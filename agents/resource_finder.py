import os
import re
import json
import time
from duckduckgo_search import DDGS
from dotenv import load_dotenv

from database.queries import insert_resources, get_curriculum_by_user, get_user_by_telegram_id
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from graph.state import LearningState

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
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY")
    )

    model_with_tools = model.bind_tools(tools)


    if not messages:
        system_prompt = f"""You are a dedicated resource retrieval system.
        Your task is to call the provided search tools to find educational materials for the following topic:
        Topic: {topic}
        Skill Level: {skill_level}

        CRITICAL DIRECTION: Select and invoke the required tools immediately. Do not write conversational greetings, explanations, or roadmaps yet. Only trigger the tools.
        """
        messages = [HumanMessage(content=system_prompt)]
        response = model_with_tools.invoke(messages)
        print(f"🔧 Initial execution: triggering tool generation calls.")
        return {"messages": messages + [response]}

    last_message = messages[-1]
    

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print(f"🔧 Retrying tool node routing for: {[t['name'] for t in last_message.tool_calls]}")
        return {"messages": messages}

    print("📝 Tool results detected. Assembling minimal, ultra-compact text layout...")
    
    final_prompt = f"""You are a personal learning planner. Review the search results provided in the message history.
    Construct a clean, ultra-compact, and minimal weekly curriculum summary using real URLs extracted from the search results.

    Follow this presentation structure exactly:
    📚 <b>Personalized Roadmap: {topic} ({skill_level})</b>

    <b>Week 1: [Topic Title]</b>
    🔗 <a href="REAL_URL_1">Resource Title 1</a> (🎥 YouTube)
    🔗 <a href="REAL_URL_2">Resource Title 2</a> (📖 Article)

    ... continue for all curriculum weeks ...
    
    👉 Reply with "Done" or "/quiz" when you finish studying!

    At the very end of your response, append a valid JSON block inside ```json and ``` markdown tags holding structural data mapping to the curriculum exactly:
    ```json
    {{
        "week_1": [
            {{"title": "Resource Title 1", "url": "REAL_URL_1", "type": "youtube"}},
            {{"title": "Resource Title 2", "url": "REAL_URL_2", "type": "article"}}
        ]
    }}
    ```
    
    CRITICAL RULES:
    1. Only use real links provided by the tools. Never hallucinate placeholding links like "https://www.youtube.com/watch?v=...".
    2. Do not include any paragraph text, introductory chat fluff, or detailed explanations. Keep it ultra-compact to avoid length errors.
    """
    
    
    assembly_messages = messages + [HumanMessage(content=final_prompt)]
    final_generation = model.invoke(assembly_messages)

    final_text = final_generation.content
    resources_per_week = {}
    user_facing_message = final_text

   
    try:
        json_match = re.search(r'\{.*\}', final_text, re.DOTALL)
        if json_match:
            clean_json = json_match.group(0)
            resources_per_week = json.loads(clean_json)
            user_facing_message = final_text.replace(json_match.group(0), "").replace("```json", "").replace("```", "").strip()
    except Exception as e:
        print(f"❌ Database resource format parsing skipped/error: {str(e)}")
        resources_per_week = {f"week_{w['week_number'] if 'week_number' in w else w.get('week', 1)}": [] for w in curriculum}

    if not user_facing_message.strip():
        user_facing_message = f"🧠 <b>Personalized Roadmap: {topic} ({skill_level})</b>\n\n"
        for week in curriculum:
            w_num = week.get("week_number") or week.get("week", 1)
            w_title = week.get("title") or week.get("module_title", "Topic Module")
            user_facing_message += f"<b>Week {w_num}: {w_title}</b>\n"
            
            week_key = f"week_{w_num}"
            week_res = resources_per_week.get(week_key, [])
            for res in week_res:
                r_type = str(res.get('type', 'youtube')).lower()
                icon = "🎥" if "youtube" in r_type else "📖" if "article" in r_type else "🎓"
                user_facing_message += f"🔗 <a href='{res.get('url', '#')}'>{res.get('title', 'Resource Link')}</a> ({icon})\n"
            user_facing_message += "\n"
        user_facing_message += "👉 Reply with <b>Done</b> or type <b>/quiz</b> when you finish studying!"

    
    try:
        user = get_user_by_telegram_id(telegram_id)
        user_id = user["id"]
        db_curriculum = get_curriculum_by_user(user_id)

        for week in db_curriculum:
            week_key = f"week_{week['week_number']}"
            resources = resources_per_week.get(week_key, [])
            if resources:
                insert_resources(curriculum_id=week["id"], resources=resources)
    except Exception as db_err:
        print(f"⚠️ Database write warning: {db_err}")

    return {
        "resources": resources_per_week,
        "response_message": user_facing_message,
        "messages": messages + [final_generation]
    }