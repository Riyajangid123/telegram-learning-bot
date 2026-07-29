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

            Return ONLY the Pydantic schema.""")
        
        self.chain = (
            self.progress_prompt
            | self.llm.with_structured_output(ProgressReport)
        )

    def track_progress(self, state:LearningState):

        report = self.chain.invoke({

            "assessment": state["skill_assessment"],

            "curriculum": state["curriculum"],

            "quiz_evaluation": state["quiz_evaluation"]

        })


        state["progress"]=report
        state["response_message"] = f"""
        📊 Progress Report

        🎯 Current Level: {report.current_level}

        📈 Overall Progress: {report.overall_progress:.1f}%

        💼 Interview Readiness: {report.interview_readiness:.1f}%

        ✅ Strong Topics:
        {chr(10).join('- ' + t for t in report.strong_topics)}

        📚 Topics to Improve:
        {chr(10).join('- ' + t for t in report.weak_topics)}

        ➡️ Next Topics:
        {chr(10).join('- ' + t for t in report.next_topics)}

        💡 Recommendation:
        {report.recommendation}
        """
        save_progress(
            user_id=state["user_id"],
            topic_id=state["topic_id"],
            report=report.model_dump()         
        )

        print("Progress",state["progress_report"])
        return state
