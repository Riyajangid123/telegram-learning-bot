from schema.schema import ResourcePlan
from agents.llm import LLM
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from langgraph.prebuilt import ToolNode
from duckduckgo_search import DDGS
from graph.state import LearningState
import time
from database.queries import save_resources
from langchain_core.messages import ToolMessage

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

    

    def resource_finder_agent(self, state: LearningState):

        if state["curriculum"] is None:
            state["response_message"] = "Curriculum generation failed."
            return state

        tool_messages = [
            m for m in state["messages"]
            if isinstance(m, ToolMessage)
        ]

        if not tool_messages:

            ai_msg = self.tool_chain.invoke({
                "curriculum": state["curriculum"]
            })

            # Let LangGraph inspect the AIMessage.
            return {
                "messages": state["messages"] + [ai_msg]
            }

        resource_plan = self.structured_chain.invoke({
            "messages": state["messages"]
        })

        state["resources"] = resource_plan

        save_resources(
            curriculum_id=state["curriculum_id"],
            resources=resource_plan.model_dump()
        )

        state["phase"] = "idle"

        msg = "📚 <b>Learning Resources</b>\n\n"

        for topic in resource_plan.resources:

            msg += f"━━━━━━━━━━━━━━━\n"
            msg += f"📌 <b>{topic.topic}</b>\n\n"

            if topic.articles:
                msg += "📄 <b>Articles</b>\n"
                for article in topic.articles:
                    msg += f"• <a href='{article.url}'>{article.title}</a>\n"

            if topic.youtube_videos:
                msg += "\n🎥 <b>YouTube</b>\n"
                for video in topic.youtube_videos:
                    msg += f"• <a href='{video.url}'>{video.title}</a>\n"

            if topic.courses:
                msg += "\n🎓 <b>Courses</b>\n"
                for course in topic.courses:
                    msg += f"• <a href='{course.url}'>{course.title}</a>\n"

            msg += "\n"

        msg += (
            "\n✅ You're all set with your learning materials!\n\n"
            "Whenever you feel ready, type <b>/quiz</b> to test your understanding of the curriculum.\n\n"
            "Good luck with your learning! 🚀"
        )

        state["response_message"] = msg

        state["phase"] = "learning"

        return state