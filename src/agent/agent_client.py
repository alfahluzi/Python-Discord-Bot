from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import tools_condition, ToolNode

from pydantic import BaseModel
from config.config import GROQ_API_KEY, MODEL_NAME, TEMPERATURE, MAX_TOKENS
from utils.logger import Logger
from agent.retriever import Retriever

class DefaultResponse(BaseModel):
    response: str
    tool_used: list[str]

class AgentClient:
    def __init__(self, model_name = MODEL_NAME, temperature = TEMPERATURE, max_token = MAX_TOKENS):
        self.logger = Logger("agent_client")
        self.logger.info(f"Inisialisasi GroqClient dengan model: {model_name}")
        
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_token
        )
        self.retriever = Retriever()
        self.memory = MemorySaver()
        self.tools = []

        self.graph = self.__setupGraph()

    def __setupGraph(self):
        # Setup node
        graph = StateGraph(state_schema=MessagesState)
        graph.add_node("assistant", self.__node_call_llm)
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

    def __node_call_llm(self, state: MessagesState):
        """Fungsi internal untuk memanggil model"""
        response = self.llm.invoke(state["messages"])
        return {"messages": response}
    
    def setTools(self, tools: list):
        self.tools = tools
    
    def addTool(self, tool):
        self.tools.append(tool)
    
    def invoke(self, thread_id: str, query: str, system_message: str = None) -> str:
        try:
            self.logger.debug(f"Mendapatkan respons untuk pesan: {query}")
            if len(self.tools) > 0:
                self.llm.bind_tools(self.tools)
            config = {"configurable": {"thread_id": thread_id}}
            messages = [
                SystemMessage(system_message or "Kamu adalah asisten AI yang membantu menjawab pertanyaan."),
                HumanMessage(query)
            ]

            result = self.graph.invoke({"messages" : messages}, config)
            last_messages = result['messages'][-1]
            self.logger.info(last_messages)
            return last_messages

        except Exception as e:
            self.logger.error(f"Error saat mendapatkan respons dari Groq: {str(e)}")
            self.logger.exception("Detail error:")
            raise