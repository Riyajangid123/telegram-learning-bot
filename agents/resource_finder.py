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
        temperature=0.3,
        api_key=os.getenv("GROQ_API_KEY")
    )

    model_with_tools = model.bind_tools(tools)

    if not messages:
        system_prompt = f"""You are a personal learning planner and resource finder. 
        Analyze the user's details and build a custom learning presentation.
        
        Topic: {topic}
        Skill Level: {skill_level}
        Curriculum: {str(curriculum)}

        Use the available tools to search for resources across the weeks.
        - youtube_search: find tutorial videos
        - search_articles: find documentation
        - search_courses: find free courses

        CRITICAL INSTRUCTION: Your response must be clean, ultra-compact, and minimal. 
        For each week, print ONLY the week number, the core topic title, and the clickable resource links. 
        Do NOT include any long descriptions, module explanations, or paragraphs.

        Follow this exact presentation structure:
        📚 <b>Personalized Roadmap: {topic} ({skill_level})</b>

        <b>Week 1: [Topic Title]</b>
        🔗 <a href="URL">Resource Title 1</a> (🎥 YouTube)
        🔗 <a href="URL">Resource Title 2</a> (📖 Article)

        <b>Week 2: [Topic Title]</b>
        🔗 <a href="URL">Resource Title 1</a> (🎓 Course)

        ...
        
        👉 Reply with "Done" or "/quiz" when you finish studying!

        At the very end of your response, append a valid JSON block inside ```json and ``` markdown tags holding structural data mapping to the curriculum exactly:
        ```json
        {{
            "week_1": [{{"title": "...", "url": "...", "type": "youtube"}}]
        }}
        ```"""
        messages = [HumanMessage(content=system_prompt)]

    response = model_with_tools.invoke(messages)

    if response.tool_calls:
        print(f"🔧 Tool called: {[t['name'] for t in response.tool_calls]}")
        return {"messages": messages + [response]}

    print("✅ Resource finder complete")
    final_text = response.content

    resources_per_week = {}
    user_facing_message = final_text

    try:
        json_match = re.search(r'\{.*\}', final_text, re.DOTALL)
        if json_match:
            clean_json = json_match.group(0)
            resources_per_week = json.loads(clean_json)
            user_facing_message = final_text.replace(json_match.group(0), "").replace("```json", "").replace("```", "").strip()
        else:
            user_facing_message = final_text
    except Exception as e:
        print(f"❌ Database resource format parsing skipped/error: {str(e)}")
        resources_per_week = {f"week_{w['week']}": [] for w in curriculum}

    if not user_facing_message.strip():
        user_facing_message = f"🧠 <b>Personalized Roadmap: {topic} ({skill_level})</b>\n\n"
        for week in curriculum:
            w_num = week.get("week", 1)
            w_title = week.get("title") or week.get("module_title", "Topic")
            user_facing_message += f"<b>Week {w_num}: {w_title}</b>\n"
            
            week_key = f"week_{w_num}"
            week_res = resources_per_week.get(week_key, [])
            for res in week_res:
                icon = "🎥" if "youtube" in res['type'].lower() else "📖" if "article" in res['type'].lower() else "🎓"
                user_facing_message += f"🔗 <a href='{res['url']}'>{res['title']}</a> ({icon})\n"
            user_facing_message += "\n"
        user_facing_message += "👉 Reply with <b>Done</b> or type <b>/quiz</b> when you finish studying!"

    user = get_user_by_telegram_id(telegram_id)
    user_id = user["id"]
    db_curriculum = get_curriculum_by_user(user_id)

    for week in db_curriculum:
        week_key = f"week_{week['week_number']}"
        resources = resources_per_week.get(week_key, [])
        if resources:
            insert_resources(curriculum_id=week["id"], resources=resources)

    return {
        "resources": resources_per_week,
        "response_message": user_facing_message,
        "messages": messages + [response]
    }