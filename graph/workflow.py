from langgraph.graph import StateGraph, START, END

from graph.state import LearningState

from agents.welcome import welcome_agent
from agents.AssessmentQuestionGenerator import AssessmentQuestionGeneratorAgent
from agents.skill_assessment_evaluator import SkillAssessmentEvaluator
from agents.curriculum_planner import CurriculumPlanner
from agents.resource_finder import ResourceFinderAgent
from agents.quiz_generation import QuizGenerationAgent
from agents.quiz_eveluator import QuizEvaluationAgent
from agents.progress_tracker import ProgressTrackerAgent


# ----------------------------
# Router
# ----------------------------
def router(state: LearningState):

    message = state.get("user_message", "").strip().lower()
    phase = state.get("phase", "")

    if message == "/start":
        return "welcome"

    elif message == "/resources":
        return "resource_finder"

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
# Build Graph
# ----------------------------
def build_graph():

    workflow = StateGraph(LearningState)

    # ----------------------------
    # Nodes
    # ----------------------------

    workflow.add_node(
        "welcome",
        welcome_agent
    )

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
    # Entry
    # ----------------------------

    workflow.add_conditional_edges(
        START,
        router,
        {
            "welcome": "welcome",
            "assessment_questions": "assessment_questions",
            "skill_assessment": "skill_assessment",
            "resource_finder": "resource_finder",
            "quiz_generation": "quiz_generation",
            "quiz_evaluation": "quiz_evaluation",
            "progress_tracker": "progress_tracker",
            END: END,
        }
    )

    # ----------------------------
    # Welcome
    # ----------------------------

    workflow.add_edge(
        "welcome",
        END
    )

    # ----------------------------
    # Assessment
    # ----------------------------

    workflow.add_edge(
        "assessment_questions",
        END
    )

    workflow.add_edge(
        "skill_assessment",
        "curriculum_planner"
    )

    workflow.add_edge(
        "curriculum_planner",
        END
    )

    # ----------------------------
    # Resources
    # ----------------------------

    workflow.add_edge(
        "resource_finder",
        END
    )

    # ----------------------------
    # Quiz
    # ----------------------------

    workflow.add_edge(
        "quiz_generation",
        END
    )

    workflow.add_edge(
        "quiz_evaluation",
        "progress_tracker"
    )

    # ----------------------------
    # Progress
    # ----------------------------

    workflow.add_edge(
        "progress_tracker",
        END
    )

    return workflow.compile()