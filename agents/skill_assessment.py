from graph.state import LearningState
from database.queries import update_user_topic_skill_level, get_user_by_telegram_id
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

def skill_assesment_agent(state: LearningState):
    telegram_id = state["telegram_id"]
    topic = state["topic"]
    user_message = state["user_message"]

    assessment_questions = state.get("assessment_questions", [])
    assessment_answers = state.get("assessment_answers", [])

    model = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        api_key=os.getenv("GROQ_API_KEY")
    )

    prompt = ChatPromptTemplate.from_template("""
        You are a skill assessment expert.
        The user wants to learn: {topic}

        Questions asked so far: {questions}
        Answers given so far: {answers}

        Your job:
        - If less than 5 questions have been asked, ask the NEXT one question only
        - If 5 questions have been asked and answered, evaluate the user and return:
            Skill Level: beginner / intermediate / advanced
            Knowledge Gaps: list the weak areas

        Rules:
        - Ask ONE question at a time
        - Questions should test practical knowledge of {topic}
        - Be conversational and friendly
        - Do not repeat questions already asked
    """)



    
    if user_message and user_message != topic:
        assessment_answers.append(user_message)

    chain = prompt | model

    response = chain.invoke({
        "topic": topic,
        "questions": assessment_questions,
        "answers": assessment_answers
    })

    
    if len(assessment_answers) >= 5:
        response_text = response.content.lower()

    
        skill_level = "beginner"

        if "advanced" in response_text:
            skill_level = "advanced"
        elif "intermediate" in response_text:
            skill_level = "intermediate"
        else:
            skill_level = "beginner"

        gaps = []
        if "knowledge gaps:" in response_text:
            gaps_section = response_text.split("knowledge gaps:")[1]
            gaps = [g.strip() for g in gaps_section.split("-") if g.strip()]

    
        update_user_topic_skill_level(
            telegram_id=telegram_id,
            topic=topic,
            skill_level=skill_level
        )

        return {
            "skill_level": skill_level,
            "knowledge_gaps": gaps,
            "assessment_answers": assessment_answers,
            "assessment_questions": assessment_questions,
            "response_message": response.content
        }

    else:
        assessment_questions.append(response.content)

        return {
            "skill_level": "",
            "knowledge_gaps": [],
            "assessment_answers": assessment_answers,
            "assessment_questions": assessment_questions,
            "response_message": response.content
        }