from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph, add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage
from langgraph.prebuilt import tools_condition, ToolNode
from langchain.tools import BaseTool

from pydantic import BaseModel
from typing import TypedDict, Annotated, List
from config.config import GROQ_API_KEY, MODEL_NAME, TEMPERATURE, MAX_TOKENS
from utils.logger import Logger
from agent.data_retriever import DataRetriever
from agent.tools import StaticTools, DynamicTools
from utils.supabase import supabase_client
from discord.ext.commands import Context

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    guild_id: str
    thread_id: str
    user_id: str

class AgentClient:
    def __init__(self, model_name = MODEL_NAME, temperature = TEMPERATURE, max_token = MAX_TOKENS):
        self.model_name = model_name
        self.temperature = temperature
        self.max_token = max_token
        self.tools = []
        self.logger = Logger(__file__)
        self.llm_logger = Logger("agent.llm")
        self.logger.info(f"Inisialisasi GroqClient dengan model: {model_name}")
        self.retriever = DataRetriever()
        self.memory = MemorySaver()
        self.tools: List[BaseTool] = StaticTools.tools + DynamicTools.tools
        
        llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_token
        )
        self.llm = llm.bind_tools(self.tools)
        self.graph = self.__setupGraph()

    def initialize_tools(self, ctx):
        """Initialize tools with Discord context"""

    def __setupGraph(self):
        # Setup node
        graph = StateGraph(state_schema=State)
        graph.add_node("assistant", self.__call_llm_node)
        graph.add_node("tools", ToolNode(self.tools))
        
        # Setup edge
        graph.add_edge(START, "assistant")
        graph.add_conditional_edges("assistant",tools_condition)
        graph.add_edge("tools", "assistant")

        # Compile graph
        graph = graph.compile(checkpointer=self.memory)

        graph_image = graph.get_graph(xray=True).draw_mermaid_png()
        with open("src/img/graph.png", "wb") as f:
            f.write(graph_image)
        
        return graph

    def __call_llm_node(self, state: State):
        """Fungsi internal untuk memanggil model"""
        response = self.llm.invoke(state["messages"])
        log_msg = {
            "thread_id": state["thread_id"],
            "user_id": state["user_id"],
            "model_name": response.response_metadata["model_name"],
            "token_usage": response.usage_metadata,
            "time_usage": {
                    "completion_time":response.response_metadata["token_usage"]["completion_time"],
                    "prompt_time":response.response_metadata["token_usage"]["prompt_time"],
                    "queue_time":response.response_metadata["token_usage"]["queue_time"],
                    "total_time":response.response_metadata["token_usage"]["total_time"],    
                }
            }
        self.llm_logger.debug(log_msg)
        return {"messages": response}
    
    def __execute_db_query_node(self, state: State):
        class __ResponseFormat(BaseModel):
            message: str
            query: str
        db_detail = ""
        humanMessage = SystemMessage(
            f"This is my database detail {db_detail}\n\n"
            "Create postgresql query base on user request"
        )
        message = state["messages"] + [humanMessage]
        tempModel = self.llm.with_structured_output(__ResponseFormat)
        rsp: __ResponseFormat = tempModel.invoke(message)
        msg = rsp.message
        query = rsp.query

        self.logger.debug(f"Execute query: {query}")
        return_msg = ""
        try:
            response = supabase_client.rpc("execute_raw_query", {"query": query}).execute()
            return_msg = "Success execute query."
            if response.data:
                return_msg = f"{return_msg}\n\n {str(response.data)}"
        except Exception as e:
            return_msg = f"Failed to execute query with error: {e}"
            self.logger.error(f"Error: {e}")
        return {"messages": f"{msg} \n\n {return_msg}"}


    def setTools(self, tools: list):
        self.tools = tools
    
    def addTool(self, tool):
        self.tools.append(tool)
    
    # def initAgent(self, thread_id: str, system_message:str = None):
    #     initial_state = {
    #         "messages": [SystemMessage(system_message or "Kamu adalah asisten AI yang membantu menjawab pertanyaan.")],
    #         "session_id": "init",
    #         "user_id": "init"
    #     }
    #     config = {"configurable": {"thread_id": thread_id}}
    #     self.graph.invoke(initial_state, config)

    def invoke(self, guild_id:str, thread_id: str, user_id: str, query: str, system_message = None) -> str:
        try:
            self.logger.debug(f"Mendapatkan respons untuk pesan: {query}")            

            initial_state: State = {
                "messages": [
                        SystemMessage(system_message or "Kamu adalah asisten AI yang membantu menjawab pertanyaan."),
                        HumanMessage(query)
                    ],
                "guild_id": guild_id,
                "thread_id": thread_id,
                "user_id": user_id or "unknown",
            }

            config = {"configurable": {"thread_id": thread_id}}
            result = self.graph.invoke(initial_state, config)
            
            for m in result['messages'][-1:]:
                self.logger.info(m.content)
                m.pretty_print()
            
            last_messages = result['messages'][-1]
            return last_messages

        except Exception as e:
            self.logger.error(f"Error saat mendapatkan respons dari Groq: {str(e)}")
            self.logger.exception("Detail error:")
            raise