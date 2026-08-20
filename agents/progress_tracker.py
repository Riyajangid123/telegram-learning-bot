from langchain_core.prompts import ChatPromptTemplate
from agents.llm import LLM
from schema.schema import ProgressReport
from graph.state import LearningState
from database.queries import save_progress

class ProgressTrackerAgent:
    def __init__(self):
        self.llm=LLM().llm()
        self.progress_prompt = ChatPromptTemplate.from_template("""
            You are an AI Learning Progress Tracker.

            Inputs

            Skill Assessment:
            {assessment}

            Curriculum:
            {curriculum}

            Quiz Evaluation:
            {quiz_evaluation}

            Analyze learner progress.

            Determine

            - mastery
            - interview readiness
            - completed topics
            - pending topics
            - weak topics
            - strong topics
            - next topics to learn

            Return only data matching the provided structured output schema.
            Do not output Python code.
            Do not output the Pydantic class.
            Do not provide explanations outside the structured result.""")
        
        self.chain = (
            self.progress_prompt
            | self.llm.with_structured_output(ProgressReport,method="function_calling")
        )

    def track_progress(self, state: LearningState):

        if not state.get("quiz_evaluation"):
            state["response_message"] = (
                "📊 I don't have enough data yet to show your progress.\n\n"
                "Please complete the quiz first with <b>/quiz</b>, then try /progress again."
            )
            return state

        report = self.chain.invoke({
            "assessment": state["skill_assessment"],
            "curriculum": state["curriculum"],
            "quiz_evaluation": state["quiz_evaluation"]
        })

        state["progress"] = report

        state["response_message"] = f"""
        📊 <b>Your Learning Progress</b>

        ✅ Current Level: {report.current_level}

        📈 Overall Progress: {report.overall_progress}%

        🏅 Interview Readiness: {report.interview_readiness}%

        💪 Strong Topics:
        {', '.join(report.strong_topics) if report.strong_topics else 'None yet'}

        ⚠️ Weak Topics:
        {', '.join(report.weak_topics) if report.weak_topics else 'None'}

        📚 Completed Topics:
        {', '.join(report.completed_topics) if report.completed_topics else 'None yet'}

        📖 Pending Topics:
        {', '.join(report.pending_topics) if report.pending_topics else 'None'}

        🔜 Next Topics:
        {', '.join(report.next_topics) if report.next_topics else 'None'}

        💡 Recommendation:
        {report.recommendation}

        Keep learning! 🚀"""

        save_progress(
            user_id=state["user_id"],
            topic_id=state["topic_id"],
            report=report.model_dump()
        )

        return state