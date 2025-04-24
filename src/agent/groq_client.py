from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.tools import VectorStoreQATool

from config.config import GROQ_API_KEY, MODEL_NAME, TEMPERATURE, MAX_TOKENS
from utils.logger import Logger
from pydantic import BaseModel
from utils.supabase import supabase_client as supabase
from utils.supabase import TableRegistry
import os
import hashlib
import uuid

class DefaultResponse(BaseModel):
    response: str
    tool_used: list[str]

class GroqClient:
    def __init__(self, model_name = MODEL_NAME, temperature = TEMPERATURE, max_token = MAX_TOKENS):
        self.logger = Logger("groq_client")
        self.logger.info(f"Inisialisasi GroqClient dengan model: {model_name}")
        
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_token
        )

        # Inisialisasi memory dengan LangGraph
        self.memory = MemorySaver()
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        self.data_registry = self.__init_vectorstore("data_registry", "match_data_registry")
        self.tool_registry = self.__init_vectorstore("tool_registry", "match_tool_registry")

        self.tools = []

        # Buat workflow graph
        self.workflow = StateGraph(state_schema=MessagesState)
        self.workflow.add_edge(START, "model")
        self.workflow.add_node("model", self._call_model)
        
        # Compile workflow dengan memory
        self.app = self.workflow.compile(checkpointer=self.memory)

    def __init_vectorstore(self, table_name: str, query_name: str) -> SupabaseVectorStore:
        return SupabaseVectorStore(
            embedding=self.embeddings,
            client=supabase,
            table_name=table_name,
            query_name=query_name,
            chunk_size=350
        )
    
    def _call_model(self, state: MessagesState):
        """Fungsi internal untuk memanggil model"""
        response = self.llm.invoke(state["messages"])
        return {"messages": response}
    
    def _create_tool_from_docs(self, docs, data_type: TableRegistry):
        tool = None
        table_name, query_name, description, attr = {
            TableRegistry.DataRegistry: ("data_registry", "match_data_registry", 
                                         "Cari informasi dari data registry internal. Data registri berisi knowledge secara umum", 
                                         "data_registry"),
            TableRegistry.ToolRegistry: ("tool_registry", "match_tool_registry", 
                                         "Cari informasi dari tool registry internal. Tool registri berisi tool yang pernah dijalankan secara aman", 
                                         "tool_registry")
        }.get(data_type, (None, None, None, None))

        if not table_name:
            raise Exception("data_type tidak valid. Gunakan enum class TableRegistry")

        store = SupabaseVectorStore.from_documents(
            docs,
            self.embeddings,
            client=supabase,
            table_name=table_name,
            query_name=query_name,
            chunk_size=500
        )

        setattr(self, attr, store)

        tool = VectorStoreQATool(
            name=f"{table_name}_search",
            description=description,
            vectorstore=store,
            llm=self.llm
        )

        self.addTool(tool)
        
    def _load_and_split_docs(self, file_path: str):
        loader = TextLoader(file_path)
        documents = loader.load()
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        return splitter.split_documents(documents)
    
    def setupKnowledge(self, data_dir: str, data_type: TableRegistry) -> None:
        """
        DANGER! This function overwrites all data on database
        """
        try:
            for file in os.listdir(data_dir):
                path = os.path.join(data_dir, file)
                if os.path.isfile(path):
                    self.logger.debug(f"File yang ditemukan: {file}")
                    docs = self._load_and_split_docs(path)
                    self._create_tool_from_docs(docs, data_type)
        except Exception as e:
            self.logger.error(f"Error saat menyiapkan pengetahuan: {e}")       
        
    def __get_text_hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def __doc_exists(self, hash_str: str, vector_store: SupabaseVectorStore) -> bool:
        try:
            results = vector_store.similarity_search(hash_str, k=1)
            return any(result.metadata.get("hash") == hash_str for result in results)
        except Exception as e:
            self.logger.error(f"Error checking duplicate: {e}")
            return False

    def addNewKnowledge(self, data_dir: str, data_type: TableRegistry) -> None:
        try:
            for file in os.listdir(data_dir):
                file_path = os.path.join(data_dir, file)
                if os.path.isfile(file_path):
                    self.logger.debug(f"File ditemukan: {file}")
                    docs = self._load_and_split_docs(file_path)

                    filtered_docs = []
                    for doc in docs:
                        hash_str = self.__get_text_hash(doc.page_content)
                        doc.metadata.update({"hash": hash_str, "source_file": file})

                        store = {
                            TableRegistry.DataRegistry: self.data_registry,
                            TableRegistry.ToolRegistry: self.tool_registry
                        }.get(data_type)

                        if not store:
                            raise Exception("data_type tidak valid")

                        if not self.__doc_exists(hash_str, store):
                            filtered_docs.append(doc)
                        else:
                            self.logger.debug(f"Duplikat dilewati: {file} / {hash_str}")

                    if filtered_docs:
                        store.add_documents(filtered_docs)
                        self.logger.info(f"{len(filtered_docs)} dokumen ditambahkan dari file {file}")
                    else:
                        self.logger.info(f"Tidak ada dokumen baru dari file {file}")
        except Exception as e:
            self.logger.error(f"Error saat menambahkan pengetahuan: {e}")
    
    def setTools(self, tools: list):
        self.tools = tools
    
    def addTool(self, tool):
        self.tools.append(tool)
    
    def invoke(self, query: str, system_message: str = "", base_model: BaseModel = DefaultResponse) -> str:
        try:
            self.logger.debug(f"Mendapatkan respons untuk pesan: {query}")
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_message + ". Kamu adalah asisten AI yang membantu menjawab pertanyaan."),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])

            agent = create_tool_calling_agent(
                llm=self.llm,
                prompt=prompt,
                tools=self.tools
            )

            executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
            raw_response = executor.invoke({"input": query}, config=config)

            result = raw_response.get("output", "[Tidak ada respons]")
            return result if result else "Tidak ada respons"

        except Exception as e:
            self.logger.error(f"Error saat mendapatkan respons dari Groq: {str(e)}")
            self.logger.exception("Detail error:")
            raise