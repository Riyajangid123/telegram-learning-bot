from typing import TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from schema.schema import (
    SkillAssessment,
    CurriculumPlan,
    ResourcePlan,
    Quiz,
    QuizEvaluation,
    ProgressReport,
    UserAnswer,
)


def keep_last(old, new):
    return new


class LearningState(TypedDict):

    messages: Annotated[list[BaseMessage], add_messages]

    response_message: Annotated[str, keep_last]

    user_message: str

    phase: str

    user_id: Optional[int]

    telegram_id: int

    username: str


    topic: str

    topic_id: Optional[int]

    curriculum_id: Optional[int]

    quiz_id: Optional[int]


    awaiting_topic: bool

    awaiting_assessment_answers: bool

    awaiting_quiz_answers: bool


    assessment_questions: list[str]

    assessment_answers: list[str]

    skill_assessment: Optional[SkillAssessment]


    curriculum: Optional[CurriculumPlan]

    resources: Optional[ResourcePlan]

    quiz: Optional[Quiz]

    user_answers: list[UserAnswer]

    quiz_evaluation: Optional[QuizEvaluation]

    progress: Optional[ProgressReport]