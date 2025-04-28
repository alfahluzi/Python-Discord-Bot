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
from utils.supabase import supabase_client
from typing import Callable
from agent.tools import Tools


class StateSchema(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    guild_id: str
    thread_id: str
    user_id: str

class AgentClient:
    def __init__(self, discord_bot, model_name = MODEL_NAME, temperature = TEMPERATURE, max_token = MAX_TOKENS):
        self.logger = Logger(__file__)
        self.llm_logger = Logger("agent.llm")
        self.logger.info(f"Initializing GroqClient with model: {model_name}, temprature: {temperature}, max_token: {max_token}")
        
        # self.retriever = DataRetriever()
        self.memory = MemorySaver()
        self.tools: List[BaseTool] = Tools(discord_bot).getTools()
        
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_token
        )
        self.llm_with_tool = self.llm.bind_tools(self.tools)
        self.graph = self.__setupGraph()

    def initialize_tools(self, ctx):
        """Initialize tools with Discord context"""
        self.logger.info("Initializing tools with Discord context")

    def __setupGraph(self):
        self.logger.info("Setting up state graph")
        # Setup node
        graph = StateGraph(state_schema=StateSchema)
        graph.add_node("assistant", self.__call_llm_node)
        graph.add_node("tools", ToolNode(self.tools))
        
        # Setup edge
        graph.add_edge(START, "assistant")
        graph.add_conditional_edges("assistant",tools_condition)
        graph.add_edge("tools", "assistant")

        # Compile graph
        self.logger.info("Compiling state graph")
        graph = graph.compile(checkpointer=self.memory)

        self.logger.info("Saving graph visualization")
        graph_image = graph.get_graph(xray=True).draw_mermaid_png()
        with open("src/img/graph.png", "wb") as f:
            f.write(graph_image)
        
        return graph

    def __call_llm_node(self, state: StateSchema):
        """Internal function to call the model"""
        self.logger.info("Calling LLM node")
        
        response = self.llm_with_tool.invoke(state["messages"])
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
        self.llm_logger.debug(response)
        return {"messages": response}
    
    def __execute_db_query_node(self, state: StateSchema):
        self.logger.info("Executing database query node")
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

        self.logger.debug(f"Executing query: {query}")
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

    def invoke(self, guild_id:str, thread_id: str, user_id: str, query: str, system_message = None) -> str:
        try:
            self.logger.info(f"Invoking agent with query: {query}")            

            initial_state: StateSchema = {
                "messages": [
                        SystemMessage(
                            (system_message or "Kamu adalah asisten AI yang membantu menjawab pertanyaan.") 
                            + (f"\nUser context:\n")
                            # + (f"- guild_id: {guild_id}\n")
                            # + (f"- thread_id: {thread_id}\n")
                            + (f"- user_id: {user_id}")
                        ),
                        HumanMessage(query)
                    ],
                "guild_id": guild_id,
                "thread_id": thread_id,
                "user_id": user_id or "guest",
            }
            self.logger.info(f"init_state: {initial_state}")
            
            config = {"configurable": {"thread_id": thread_id}}
            result = self.graph.invoke(initial_state, config)
            
            for m in result['messages'][-1:]:
                self.logger.info(f"Agent response: {m.content}")
                m.pretty_print()
            
            last_messages = result['messages'][-1]
            return last_messages

        except Exception as e:
            self.logger.error(f"Error getting response from Groq: {str(e)}")
            return self.llm.invoke([
                SystemMessage("You are an agent ai with expertise in python, discord bot, langgraph, langchain. You can explain briefly in maximum 2000 character"),
                HumanMessage(f"Help me explain and give suggestion about this error:\n{e}")
            ])