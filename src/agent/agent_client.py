from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import START, StateGraph, add_messages, END
from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage
from langchain_core.tools import StructuredTool
from langchain_core.documents import Document

from typing import TypedDict, Annotated, List
from config.config import GROQ_API_KEY, MODEL_NAME, TEMPERATURE, MAX_TOKENS
from langchain_core.messages import RemoveMessage

from agent.tools import Tools
from agent.data_retriever import DataRetriever

from utils.logger import Logger
from utils.supabase import TableRegistry

from typing import Literal
from datetime import datetime
from transformers import BertTokenizerFast
import os
from dotenv import load_dotenv
load_dotenv()
mode = os.getenv("MODE")

class StateSchema(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    summary: str
    guild_id: str
    thread_id: str
    user_id: str

class AgentClient:
    def __init__(self, discord_bot, model_name = MODEL_NAME, temperature = TEMPERATURE, max_token = MAX_TOKENS):
        self.logger = Logger(__file__)
        self.llm_logger = Logger("agent.llm")
        self.logger.info(f"Initializing GroqClient with model: {model_name}, temprature: {temperature}, max_token: {max_token}")
        
        self.retriever = DataRetriever()
        self.retriever.setupKnowledge(
            data_dir="src/data/knowledges",
            data_type=TableRegistry.DataRegistry,
        )
        self.memory = MemorySaver()
        self.tokenizer = BertTokenizerFast.from_pretrained("bert-base-uncased")
        self.tools: List[StructuredTool] = Tools(self, discord_bot).getTools()
        
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_token
        )
        self.llm_with_tool = self.llm.bind_tools(self.tools)
        self.graph = self.__setupGraph()

    def __setupGraph(self):
        self.logger.info("Setting up state graph")
        # Setup node
        graph = StateGraph(state_schema=StateSchema)
        graph.add_node("assistant", self.__async_call_llm_node)
        graph.add_node("tools", ToolNode(self.tools,handle_tool_errors=True))
        graph.add_node("summarizer", self.__summary_node)
        
        # Setup edge
        graph.add_edge(START, "assistant")
        # graph.add_conditional_edges("assistant", tools_condition)
        graph.add_conditional_edges("assistant", self.__custom_tools_condition)
        graph.add_edge("tools", "assistant")
        graph.add_edge("summarizer", END)

        # Compile graph
        self.logger.info("Compiling state graph")
        graph = graph.compile(checkpointer=self.memory)

        self.logger.info("Saving graph visualization")
        graph_image = graph.get_graph(xray=True).draw_ascii()
        self.logger.info(f"Graph\n{graph_image}")
        # with open("src/img/graph.png", "wb") as f:
        #     f.write(graph_image)
        
        return graph
    
    async def __summary_node(self, state: StateSchema):
        """
        Node ini bertugas untuk membuat ringkasan dari percakapan yang sedang berlangsung.
        Jika panjang token pesan kurang dari 750, maka tidak ada ringkasan yang dibuat.
        Jika ada ringkasan sebelumnya, maka ringkasan baru akan dibuat dengan memperbarui ringkasan lama.
        Setelah membuat ringkasan, pesan-pesan lama akan dihapus dan ringkasan baru akan disimpan.
        
        Args:
            state (StateSchema): State yang berisi informasi tentang percakapan.

        Returns:
            dict: Dengan kunci "summary" yang berisi ringkasan baru dan "messages" yang berisi daftar pesan yang harus dihapus.
        """
        token = self.tokenizer.encode(" ".join([msg.content for msg in state["messages"]]), add_special_tokens=False)
        self.logger.info(f"[Summary Node], total token: {len(token)}")
        if len(token) < 750:
            self.logger.info("Token length is less than 750")
            return {"summary": ""}
        
        self.logger.info("Token length is greater than 750, create summary...")
        summary = state.get("summary", "")
        if summary:
            prompt = (
                f"This is a summary of the conversation to date: {summary}\n\n"
                "Extend the summary by taking into account the new messages above:"
            )
        else: prompt = "Create a summary of the conversation above:"

        messages = state["messages"] + [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages)

        self.logger.info("Saving summary to database...")
        self.retriever.saveData(
            query=response.content,
            meta_data={
                "source":"summary",
                "create_at": datetime.now().isoformat(),
                "author":"system",
            },
            data_type=TableRegistry.DataRegistry
        )

        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
        return {"summary": response.content, "messages": delete_messages}

    def __custom_tools_condition(
        self,
        state: StateSchema,
        messages_key: str = "messages",
    ) -> Literal["tools", "summarizer"]:
        """
        Menentukan apakah state harus diarahkan ke node "tools" atau "summarizer" 
        berdasarkan adanya panggilan tool dalam pesan terakhir.

        Args:
            state (Union[list[AnyMessage], dict[str, Any], BaseModel]): State yang sedang diproses.
            messages_key (str, optional): Kunci untuk mengakses daftar pesan dalam state. Defaults to "messages".

        Returns:
            Literal["tools", "summarizer"]: Node yang harus dituju berikutnya.
        """
        self.logger.info("[Tool Condition Node]")
        # Kalau StateSchema (dict)
        if isinstance(state, dict) and (messages := state.get(messages_key, [])):
            ai_message = messages[-1]
            self.logger.info(f"Ai Message: {ai_message}")
        else:
            raise TypeError(f"Unexpected type for state: {type(state)}")

        # Cek tool_calls
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"
        return "summarizer"

    async def __async_call_llm_node(self, state: StateSchema):
        """Internal function to call the model"""
        self.logger.info("[Calling LLM Node]")
        
        response = await self.llm_with_tool.ainvoke(state["messages"])
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
    
    async def invoke(self, guild_id: str, thread_id: str, user_id: str, query: str, system_message: str = None) -> str:
        """
        Menginvoke agen dengan query yang diberikan dan mengembalikan respons terakhir.

        Args:
            guild_id (str): ID guild yang terkait dengan query.
            thread_id (str): ID thread yang terkait dengan query.
            user_id (str): ID user yang mengajukan query.
            query (str): Query yang ingin dijawab oleh agen.
            system_message (str, optional): Pesan sistem yang ingin ditambahkan ke konteks. Defaults to None.

        Returns:
            str: Respons terakhir dari agen.
        """
        try:
            self.logger.info(f"Invoking agent with query: {query}")            
            knowledges: List[tuple[Document, float]] = self.retriever.loadData(query, TableRegistry.DataRegistry)
            knowledge: List[str] = [kl[0].page_content for kl in knowledges]
            
            initial_state: StateSchema = {
                "messages": [
                        SystemMessage(
                            (system_message or "Kamu adalah asisten AI yang membantu menjawab pertanyaan.\n") 
                            + (f"\nUser context:\n")
                            # + (f"- guild_id: {guild_id}\n")
                            # + (f"- thread_id: {thread_id}\n")
                            + (f"- user_id: {user_id}\n")
                            + (f"\nKnowledge context:\n")
                            + (" ".join(knowledge))
                        ),
                        HumanMessage(query)
                    ],
                "summary": "",
                "guild_id": guild_id,
                "thread_id": thread_id,
                "user_id": user_id or "guest",
            }
            self.logger.info(f"init_state: {initial_state}")
            
            config = {"configurable": {"thread_id": thread_id}}
            result = await self.graph.ainvoke(initial_state, config)
            
            for m in result['messages'][-1:]:
                self.logger.info(f"Agent response: {m.content}")
                m.pretty_print()
            
            last_messages = result['messages'][-1]
            return last_messages

        except Exception as e:
            self.logger.error(f"Error getting response from Groq: {str(e)}")
            raise