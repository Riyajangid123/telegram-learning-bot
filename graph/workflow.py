from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from agents.skill_assessment import skill_assesment_agent
from agents.curriculum_planner import curriculum_planner_agent
from agents.resource_finder import resource_finder_agent, tool_node  
from agents.quiz_generation import quiz_generation_agent
from agents.progress_tracker import progress_tracker_agent
from langgraph.prebuilt import tools_condition
from graph.state import LearningState

def build_graph():
    workflow = StateGraph(LearningState)

    workflow.add_node("skill_assessment", skill_assesment_agent)
    workflow.add_node("curriculum_planner", curriculum_planner_agent)
    workflow.add_node("resource_finder", resource_finder_agent)
    workflow.add_node("tools", tool_node)         
    workflow.add_node("quiz_generation", quiz_generation_agent)
    workflow.add_node("track_progress", progress_tracker_agent)

    workflow.add_edge(START, "skill_assessment")
    workflow.add_edge("skill_assessment", "curriculum_planner")
    workflow.add_edge("curriculum_planner", "resource_finder")
    workflow.add_conditional_edges("resource_finder", tools_condition) 
    workflow.add_edge("tools", "resource_finder")  
    workflow.add_edge("resource_finder", "quiz_generation")
    workflow.add_edge("quiz_generation", "track_progress")
    workflow.add_edge("track_progress", END)

    return workflow.compile()