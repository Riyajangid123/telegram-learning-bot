from graph.state import LearningState


def welcome_agent(state: LearningState):

    state["phase"] = "awaiting_topic"

    state["response_message"] = """
        👋 Welcome to AI Learning Bot!

        I'm your personal AI-powered learning assistant.

        I can help you:

        📚 Assess your current knowledge
        🛣️ Create a personalized learning roadmap
        🎥 Recommend the best learning resources
        📝 Generate quizzes
        📈 Track your learning progress

        To begin, simply tell me what you'd like to learn.

        Examples:
        • Machine Learning
        • Creative Writing
        • English
        • Painting
        • Generative AI
        """

    return state