from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from graph.state import LearningState

from agents.welcome import welcome_agent
from agents.AssessmentQuestionGenerator import AssessmentQuestionGeneratorAgent
from agents.skill_assessment_evaluator import SkillAssessmentEvaluator
from agents.curriculum_planner import CurriculumPlanner
from agents.resource_finder import ResourceFinderAgent,tools
from agents.quiz_generation import QuizGenerationAgent
from agents.quiz_eveluator import QuizEvaluationAgent
from agents.progress_tracker import ProgressTrackerAgent


tool_node = ToolNode(tools)


# ----------------------------
# Router
# ----------------------------
def router(state: LearningState):

    message = state["user_message"].strip().lower()
    phase = state.get("phase", "")

    if message == "/start":
        return "welcome"

    elif message == "/quiz":
        return "quiz_generation"

    elif message == "/progress":
        return "progress_tracker"

    elif phase == "awaiting_topic":
        return "assessment_questions"

    elif phase == "awaiting_assessment_answers":
        return "skill_assessment"

    elif phase == "awaiting_quiz_answers":
        return "quiz_evaluation"

    return END


# ----------------------------
# Graph
# ----------------------------
workflow = StateGraph(LearningState)


workflow.add_node("welcome", welcome_agent)

workflow.add_node(
    "assessment_questions",
    AssessmentQuestionGeneratorAgent().assessment_question_generator
)

workflow.add_node(
    "skill_assessment",
    SkillAssessmentEvaluator().skill_assessment_evaluate
)

workflow.add_node(
    "curriculum_planner",
    CurriculumPlanner().curriculum_generation
)

workflow.add_node(
    "resource_finder",
    ResourceFinderAgent().resource_finder_agent
)

workflow.add_node(
    "tools",
    tool_node
)

workflow.add_node(
    "quiz_generation",
    QuizGenerationAgent().quiz_generation
)

workflow.add_node(
    "quiz_evaluation",
    QuizEvaluationAgent().evaluate
)

workflow.add_node(
    "progress_tracker",
    ProgressTrackerAgent().track_progress
)


# ----------------------------
# Start
# ----------------------------
workflow.add_conditional_edges(
    START,
    router,
    {
        "welcome": "welcome",
        "assessment_questions": "assessment_questions",
        "skill_assessment": "skill_assessment",
        "quiz_generation": "quiz_generation",
        "quiz_evaluation": "quiz_evaluation",
        "progress_tracker": "progress_tracker",
        END: END,
    },
)


# ----------------------------
# Welcome
# ----------------------------
workflow.add_edge(
    "welcome",
    END,
)


# ----------------------------
# Assessment Flow
# ----------------------------
workflow.add_edge(
    "assessment_questions",
    END,
)

workflow.add_edge(
    "skill_assessment",
    "curriculum_planner",
)

workflow.add_edge(
    "curriculum_planner",
    "resource_finder",
)


# ----------------------------
# Resource Finder + Tools
# ----------------------------
workflow.add_conditional_edges(
    "resource_finder",
    tools_condition,
)

workflow.add_edge(
    "tools",
    "resource_finder",
)

workflow.add_edge(
    "resource_finder",
    END,
)


# ----------------------------
# Quiz Flow
# ----------------------------
workflow.add_edge(
    "quiz_generation",
    END,
)

workflow.add_edge(
    "quiz_evaluation",
    "progress_tracker",
)

workflow.add_edge(
    "progress_tracker",
    END,
)


build_graph = workflow.compile()