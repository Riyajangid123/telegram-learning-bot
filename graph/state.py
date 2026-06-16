from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def keep_last(old, new):
    return new

class LearningState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    telegram_id: int
    username: str
    topic: str
    user_message: str
    skill_level: str
    

    assessment_questions: list[str]
    assessment_answers: list[str]
    knowledge_gaps: list[str]
    
    curriculum: list[dict]
    resources: dict
    current_module: int

    quiz_questions: list[dict]
    user_answers: list[str]          
    awaiting_quiz_answers: bool

    quiz_score: int
    quiz_total: int
    completed_modules: list[int]   
    quiz_scores: dict        
    progress_report: str        
    next_module: str        
    response_message: Annotated[str, keep_last]