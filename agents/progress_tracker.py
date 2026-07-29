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
        📊 <b>Your Learning Progress</b>

        ✅ Mastery: {report.mastery_level}

        🏅 Interview Readiness:
        {report.interview_readiness}

        💪 Strong Topics:
        {', '.join(report.strong_topics)}

        ⚠️ Weak Topics:
        {', '.join(report.weak_topics)}

        📚 Completed Topics:
        {', '.join(report.completed_topics)}

        📖 Next Topics:
        {', '.join(report.next_topics)}

        📝 Summary:
        {report.summary}

        Keep learning! 🚀"""
        
        save_progress(
            user_id=state["user_id"],
            topic_id=state["topic_id"],
            report=report.model_dump()         
        )

        print("Progress",state["progress_report"])
        return state
