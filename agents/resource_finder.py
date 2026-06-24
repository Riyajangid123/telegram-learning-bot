from database.queries import insert_resources, get_curriculum_by_user, get_user_by_telegram_id
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from duckduckgo_search import DDGS
import json
import re
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


import re

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

        Use the available tools to search for:
        - youtube_search: find tutorial videos
        - search_articles: find documentation
        - search_courses: find free courses

        CRITICAL INSTRUCTION: Your final response MUST have two parts:
        
        PART 1 (User Message): Write a warm, interactive overview message explaining that you evaluated their background and generated a custom roadmap for their skill level ({skill_level}). Mention how many weeks it has and give them instructions. Include the list of resource links clearly.
        
        PART 2 (Data Block): At the very end, append a valid JSON block inside ```json and ``` markdown tags holding structural data mapping to the curriculum exactly:
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
    try:
        json_match = re.search(r'\{.*\}', final_text, re.DOTALL)
        if json_match:
            clean_json = json_match.group(0)
            resources_per_week = json.loads(clean_json)
            
            user_facing_message = final_text.replace(json_match.group(0), "").replace("```json", "").replace("```", "").strip()
        else:
            user_facing_message = final_text
    except Exception as e:
        print(f"❌ Resource parsing error: {str(e)}")
        user_facing_message = ""
        resources_per_week = {f"week_{w['week']}": [] for w in curriculum}

    if not user_facing_message:
        user_facing_message = f"""
        🧠 <b>Personalized Curriculum Ready!</b>

        I've evaluated your responses and structured a personalized roadmap for mastering <b>{topic}</b> tailored specifically to a <b>{skill_level}</b> tier.

        📚 We've created a custom {len(curriculum)}-week track for you. 

        Type /startlesson to view your Week 1 learning modules and access your custom reference material link dashboard directly!
        """

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