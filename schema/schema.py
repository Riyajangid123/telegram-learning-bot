from typing import List, Literal,Optional
from pydantic import BaseModel, Field


class SkillAssessment(BaseModel):

    level: Literal[
        "Beginner",
        "Intermediate",
        "Advanced",
        "Expert"
    ]

    overall_score: int = Field(
        ge=0,
        le=100
    )

    strengths: List[str]

    areas_of_improvement: List[str]

    summary: str

    confidence: Literal[
        "Low",
        "Medium",
        "High"
    ]


class CurriculumTopic(BaseModel):
    topic: str = Field(
        description="Name of the topic."
    )

    reason: str = Field(
        description="Why this topic is included."
    )

    difficulty: Literal[
        "Beginner",
        "Intermediate",
        "Advanced"
    ] = Field(
        description="Difficulty level of this topic."
    )

    estimated_hours: int = Field(
        ge=1,
        description="Estimated study hours."
    )

    learning_objectives: List[str] = Field(
        description="Learning goals."
    )

    practice_tasks: List[str] = Field(
        description="Hands-on exercises or coding tasks."
    )


class CapstoneProject(BaseModel):
    title: str = Field(
        description="Project title."
    )

    description: str = Field(
        description="Brief description of the project."
    )

    skills_covered: List[str] = Field(
        description="Skills practiced in the project."
    )

    estimated_hours: int = Field(
        ge=1,
        description="Estimated project duration."
    )


class InterviewPreparation(BaseModel):
    coding_topics: List[str] = Field(
        description="Coding topics to revise."
    )

    theory_topics: List[str] = Field(
        description="Conceptual topics to revise."
    )

    mock_interviews: int = Field(
        ge=0,
        description="Recommended number of mock interviews."
    )


class CurriculumPlan(BaseModel):
    target_level: Literal[
        "Beginner",
        "Intermediate",
        "Advanced",
        "Expert"
    ] = Field(
        description="Target level after completing the curriculum."
    )

    total_estimated_hours: int = Field(
        ge=1,
        description="Total estimated study time."
    )

    learning_path: List[CurriculumTopic] = Field(
        description="Ordered learning roadmap."
    )

    capstone_project: Optional[CapstoneProject] = None

    interview_preparation: InterviewPreparation

    success_criteria: List[str] = Field(
        description="Criteria indicating successful completion."
    )

    final_recommendation: str = Field(
        description="Overall guidance for the learner."
    )


class LearningResource(BaseModel):
    title: str
    resource_type: Literal[
        "video",
        "article",
        "documentation",
        "course",
        "tutorial",
        "practice"
    ]
    url: str
    description: str
    estimated_minutes: int


class ResourcePlan(BaseModel):
    topic: str
    skill_level: str
    areas_of_improvement: List[str]
    resources: List[LearningResource]


class TopicResources(BaseModel):
    topic: str
    articles: List[LearningResource]
    youtube_videos: List[LearningResource]
    courses: List[LearningResource]


class QuizQuestion(BaseModel):
    question: str = Field(description="Quiz question")

    topic: str = Field(description="Topic from curriculum")

    type: Literal[
        "MCQ",
        "TrueFalse",
        "Coding"
    ]

    difficulty: Literal[
        "Easy",
        "Medium",
        "Hard"
    ]

    options: Optional[List[str]] = None

    correct_answer: str

    explanation: str

    marks: int


class Quiz(BaseModel):
    total_questions: int

    estimated_time: int

    questions: List[QuizQuestion]


class QuestionEvaluation(BaseModel):

    question: str

    user_answer: str

    correct_answer: str

    is_correct: bool

    explanation: str

    topic: str

    marks_awarded: int


class QuizEvaluation(BaseModel):

    total_questions: int

    correct_answers: int

    score: float

    strengths: List[str]

    weak_topics: List[str]

    revision_topics: List[str]

    feedback: List[QuestionEvaluation]

    overall_feedback: str


class TopicProgress(BaseModel):

    topic: str

    mastery: float

    quizzes_attempted: int

    average_score: float

    status: Literal[
        "Not Started",
        "In Progress",
        "Mastered"
    ]


class ProgressReport(BaseModel):

    current_level: Literal[
        "Beginner",
        "Intermediate",
        "Advanced",
        "Expert"
    ]

    overall_progress: float

    interview_readiness: float

    strong_topics: List[str]

    weak_topics: List[str]

    completed_topics: List[str]

    pending_topics: List[str]

    topic_progress: List[TopicProgress]

    next_topics: List[str]

    recommendation: str

class UserAnswer(BaseModel):
    question_id: int
    answer: str