from schema.schema import ResourcePlan
from agents.llm import LLM
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from langgraph.prebuilt import ToolNode
from duckduckgo_search import DDGS
from graph.state import LearningState
import time
from database.queries import save_resources

@tool 
def search_articles(query: str) -> str: 
    """Search for articles and documentation on a topic""" 
    try: 
        time.sleep(2) 
        with DDGS() as ddgs: 
            results = list(ddgs.text(query, max_results=2)) 
            if not results: 
                return "No results found" 
            output = [] 
            for r in results: 
                output.append(f"Title: {r['title']}\nURL: {r['href']}\n") 
            return "\n".join(output) 
    except Exception as e: 
        return f"Search unavailable: {str(e)}" 

@tool 
def youtube_search(query: str) -> str: 
    """Search for YouTube tutorial videos on a topic""" 
    try: 
        time.sleep(2) 
        with DDGS() as ddgs: 
            results = list(ddgs.videos( f"{query} tutorial", max_results=2 )) 
            if not results: 
                return "No videos found" 
            output = [] 
            for r in results: 
                output.append(f"Title: {r['title']}\nURL: {r['content']}\n") 
            return "\n".join(output) 
    except Exception as e: 
        return f"Search unavailable: {str(e)}" 

@tool 
def search_courses(query: str) -> str: 
    """Search for free online courses on a topic""" 
    try: 
        time.sleep(2) 
        with DDGS() as ddgs: 
            results = list(ddgs.text( f"{query} free course site:coursera.org OR site:freecodecamp.org", max_results=2 )) 
            if not results: 
                return "No courses found" 
            output = [] 
            for r in results: 
                output.append(f"Title: {r['title']}\nURL: {r['href']}\n") 
            return "\n".join(output) 
    except Exception as e: 
        return f"Search unavailable: {str(e)}" 
    
tools = [search_articles, youtube_search, search_courses] 
tool_node = ToolNode(tools) 

class ResourceFinderAgent:
    def __init__(self):
        self.llm = LLM().llm()
        self.tool_prompt = ChatPromptTemplate.from_template("""
            You are an AI Resource Finder.

            Curriculum:
            {curriculum}

            For every topic, use the available tools to find:
            - Articles
            - YouTube tutorials
            - Free courses

            Always call the appropriate tools before answering.
            """)

        self.tool_llm = self.llm.bind_tools(tools)

        self.tool_chain = self.tool_prompt | self.tool_llm

        self.format_prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """
            You are an AI Resource Organizer.

            Use the ToolMessages to build the ResourcePlan.

            Return ONLY the Pydantic schema.
            """
                ),
                ("placeholder", "{messages}")
            ])

        self.structured_chain = (
            self.format_prompt
            | self.llm.with_structured_output(ResourcePlan)
        )

    def resource_finder_agent(self,state:LearningState):
        if state["curriculum"] is None:

            state["response_message"] = (
                "Curriculum generation failed. Please try again."
            )

            return state
        topics = [
        {
            "topic": t.topic,
            "difficulty": t.difficulty
        }
        for t in state["curriculum"].learning_path
        ]
        ai_msg = self.tool_chain.invoke({
        "curriculum": state["curriculum"]
        })

        tool_output = tool_node.invoke({
        "messages": [ai_msg]
        })

        messages = tool_output["messages"]

        resource_plan = self.structured_chain.invoke({
            "messages":messages
        })

        state["resources"] = resource_plan
        state["phase"] = "idle"

        state["response_message"] = f"""
        ✅ Skill Level: {state['skill_assessment'].level}

        Your personalized roadmap is ready.

        Use

        /quiz

        whenever you're ready to test yourself.

        Happy Learning 🚀
        """
        save_resources(
            curriculum_id=state["curriculum_id"],
            resources=resource_plan.model_dump()   
        )

        print("resources founded",state["resources"])
        return state