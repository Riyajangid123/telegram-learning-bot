from langchain_core.prompts import ChatPromptTemplate
from database.queries import insert_curriculum, get_user_by_telegram_id
from graph.state import LearningState
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import json
import os

load_dotenv()

def curriculum_planner_agent(state: LearningState):
    model = ChatGroq(
         model="llama-3.3-70b-versatile",
         temperature=0.3,
         api_key=os.getenv("GROQ_API_KEY")
    )

    telegram_id = state["telegram_id"]
    topic = state.get("topic", "")
    skill_level = state.get("skill_level", "")
    knowledge_gap = state.get("knowledge_gaps", [])

    prompt = ChatPromptTemplate.from_template(
        """You are a planner expert.

        User wants to learn: {topic}
        Their skill level: {skill_level}
        Their knowledge gaps: {knowledge_gaps}
    
        Generate a structured week by week curriculum plan.
        
        Rules:
        - Beginner → 6 weeks
        - Intermediate → 4 weeks
        - Pro → 2 weeks
        - Each week should build on the previous one
        - Cover the knowledge gaps specifically
        - Keep it practical and project based
        
            Return ONLY a JSON like this, nothing else:
        {{
            "curriculum": [
                {{
                    "week": 1,
                    "title": "Python Basics",
                    "description": "Variables, loops, functions",
                    "topics": ["variables", "loops", "functions"]
                }},
                {{
                    "week": 2,
                    "title": "Data Structures",
                    "description": "Lists, dicts, sets",
                    "topics": ["lists", "dictionaries", "sets"]
                }}
            ]
        }}
        """
    )

    chain = prompt | model

    response = chain.invoke({
        "topic": topic,
        "skill_level": skill_level,
        "knowledge_gaps": knowledge_gap
    })

    clean = (response.content.replace("```json", "").replace("```", "").strip())

    try:
        data = json.loads(clean)
        curriculum = data["curriculum"]
    except Exception as e:
        print(f"Curriculum parse error: {e}")
        return {
            "response_message": "Unable to generate curriculum right now."
        }

    user = get_user_by_telegram_id(telegram_id)

    if not user:
        raise ValueError(
            f"No user found for telegram_id={telegram_id}"
        )

    user_id = user["id"]

    insert_curriculum(
        user_id=user_id,
        curriculum=curriculum
    )
    
    message_lines = [
        f"🎯 <b>Your custom {skill_level.capitalize()} Roadmap for {topic.upper()} is ready!</b>\n",
    ]

    for week in curriculum:
        message_lines.append(
            f"• <b>Week {week['week']}:</b> {week['title']}"
        )

    message_lines.append("\n" + "─" * 20)
    message_lines.append("⏳ <b>Step 2/2: Fetching matching learning materials...</b>")
    message_lines.append("<i>I am using DuckDuckGo to search for relevant YouTube tutorials, documentation, and free courses for each week. Please hold on...</i>")

    response_message = "\n".join(message_lines)

    return {
        "curriculum": curriculum,
        "phase": "learning",
        "response_message": response_message
    }