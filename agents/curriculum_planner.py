from langchain_core.prompts import ChatPromptTemplate
from database.queries import insert_curriculum,get_user_by_telegram_id
from graph.state import LearningState
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import json
import os

load_dotenv()

def curriculum_planner_agent(state:LearningState):
    model=ChatGroq(
         model="llama-3.3-70b-versatile",
         temperature=0.3,
         api_key=os.getenv("GROQ_API_KEY")
    )

    telegram_id=state["telegram_id"]
    topic=state.get("topic","")
    skill_level=state.get("skill_level","")
    knowledge_gap=state.get("knowledge_gaps",[])

    prompt=ChatPromptTemplate.from_template(
        """You are a curriculum planner expert.

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
    """)

    chain=prompt|model

    response=chain.invoke({
        "topic":topic,
        "skill_level":skill_level,
        "knowledge_gaps":knowledge_gap
    })

    curriculum=json.loads(response.content)["curriculum"]

    telegram_id = state["telegram_id"]

    print("=" * 50)
    print("STATE:", state)
    print("TELEGRAM ID:", telegram_id)

    user = get_user_by_telegram_id(telegram_id)

    print("USER:", user)
    print("=" * 50)

    if user is None:
        raise ValueError(
            f"No user found for telegram_id={telegram_id}"
        )

    user_id = user["id"]


    user=get_user_by_telegram_id(telegram_id)
    user_id=user["id"]
    insert_curriculum(
        user_id=user_id,
        curriculum=curriculum
    )

    clean = response.content.replace("```json", "").replace("```", "")
    data = json.loads(clean)

    curriculum=data["curriculum"]

    message_lines=[f"Your {skill_level.capitalize()} Learning Plan for {topic}:\n"]
    for week in curriculum:
        message_lines.append(f"📅 Week {week['week']}:{week['title']}")
        message_lines.append(f"📅 {week['description']}\n")

    response_message = "\n".join(message_lines)
    response_message += "\nI'll send you daily lessons starting tomorrow at 9 AM!"

    return {
        "curriculum":curriculum,
        "response_message":response_message
    }



