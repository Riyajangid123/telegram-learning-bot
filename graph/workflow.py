from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from agents.skill_assessment import skill_assesment_agent
from agents.curriculum_planner import curriculum_planner_agent
from agents.resource_finder import resource_finder_agent, tool_node  
from agents.quiz_generation import quiz_generation_agent
from agents.progress_tracker import progress_tracker_agent
from langgraph.prebuilt import tools_condition
from graph.state import LearningState
from database.queries import get_user_by_telegram_id, get_curriculum_by_user,insert_user

def router_node(state: LearningState):
    """Determines where to route the incoming Telegram message."""
    user_message = state.get("user_message", "").strip().lower()
    telegram_id = state["telegram_id"]
    
    if user_message == "/quiz":
        return {"response_message": "Loading quiz...", "user_message": user_message}
    if user_message == "/progress":
        return {"response_message": "Loading progress report...", "user_message": user_message}
        
    user = get_user_by_telegram_id(telegram_id)
    if user and user.get("skill_level"):
        curriculum = get_curriculum_by_user(user["id"])
        if curriculum:
            return {"user_message": user_message}
            
    return {"user_message": user_message}


def welcome_node(state):
    return {
        "phase": "awaiting_topic",
        "response_message": """
        👋 Welcome to AI Learning Bot!

        I'm your personal AI learning assistant.

        🚀 Here's how I can help you:

        ✅ Assess your current skill level
        ✅ Create a personalized learning roadmap
        ✅ Recommend resources
        ✅ Generate quizzes
        ✅ Track progress

        📚 What would you like to learn today?

        Examples:
        • Python
        • Machine Learning
        • SQL
        • Data Structures
        """
    }


def route_entry(state):

    user_message = state.get("user_message", "").strip().lower()

    if user_message == "/start":
        return "welcome"

    if user_message == "/quiz":
        return "quiz_generation"

    if user_message == "/progress":
        return "track_progress"

    phase = state.get("phase")

    if phase == "awaiting_topic":
        return "skill_assessment"

    if phase == "assessment":
        return "skill_assessment"

    if phase == "learning":
        return "resource_finder"

    return "welcome"

def route_assessment(state):

    if state.get("phase") == "learning":
        return "curriculum_planner"

    return END

def build_graph():
    workflow = StateGraph(LearningState)


    workflow.add_node("router", router_node)
    workflow.add_node("welcome", welcome_node)
    workflow.add_node("skill_assessment", skill_assesment_agent)
    workflow.add_node("curriculum_planner", curriculum_planner_agent)
    workflow.add_node("resource_finder", resource_finder_agent)
    workflow.add_node("tools", tool_node)          
    workflow.add_node("quiz_generation", quiz_generation_agent)
    workflow.add_node("track_progress", progress_tracker_agent)


    workflow.add_edge(START, "router")
    
    workflow.add_conditional_edges(
        "router",
        route_entry,
        {   "welcome": "welcome",
            "skill_assessment": "skill_assessment",
            "quiz_generation": "quiz_generation",
            "track_progress": "track_progress"
        }
    )
    
    workflow.add_conditional_edges(
        "skill_assessment",
        route_assessment,
        {
            "curriculum_planner": "curriculum_planner",
            END: END
        }
    )
    
    workflow.add_edge("curriculum_planner", "resource_finder")
    workflow.add_conditional_edges("resource_finder", tools_condition) 
    workflow.add_edge("tools", "resource_finder")  
    workflow.add_edge("resource_finder", END) 
    workflow.add_edge("welcome", END)
    

    workflow.add_edge("quiz_generation", END)
    workflow.add_edge("track_progress", END)

    return workflow.compile()