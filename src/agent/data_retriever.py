from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.document_loaders import TextLoader
from langchain_community.tools import VectorStoreQATool

from utils.supabase import supabase_client
from utils.logger import Logger
from utils.supabase import TableRegistry

import hashlib
import os
class DataRetriever():
    def __init__(self) -> None:
        self.logger = Logger(__file__)
        self.logger.info(f"Inisialisasi Retriever")

        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.databases = {
            "data_registry": self.__init_vectorstore("data_registry", "match_data_registry"),
            "tool_registry": self.__init_vectorstore("tool_registry", "match_tool_registry")
        }

    def __init_vectorstore(self, table_name: str, query_name: str) -> SupabaseVectorStore:
        return SupabaseVectorStore(
            embedding=self.embeddings,
            client=supabase_client,
            table_name=table_name,
            query_name=query_name,
            chunk_size=350
        )
        
    def setupKnowledge(self, data_dir: str, data_type: TableRegistry) -> None:
        """
        DANGER! This function overwrites all data on database
        """
        try:
            for file in os.listdir(data_dir):
                path = os.path.join(data_dir, file)
                if os.path.isfile(path):
                    self.logger.debug(f"File yang ditemukan: {file}")
                    docs = self.__load_and_split_docs(path)
                    self.__create_tool_from_docs(docs, data_type)
        except Exception as e:
            self.logger.error(f"Error saat menyiapkan pengetahuan: {e}")       
       
    def saveData(self, data_dir: str, data_type: TableRegistry) -> None:
        try:
            for file in os.listdir(data_dir):
                file_path = os.path.join(data_dir, file)
                if os.path.isfile(file_path):
                    self.logger.debug(f"File ditemukan: {file}")
                    docs = self.__load_and_split_docs(file_path)

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

    def getData(self):
        pass

    def __get_text_hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def __doc_exists(self, hash_str: str, vector_store: SupabaseVectorStore) -> bool:
        try:
            results = vector_store.similarity_search(hash_str, k=1)
            return any(result.metadata.get("hash") == hash_str for result in results)
        except Exception as e:
            self.logger.error(f"Error checking duplicate: {e}")
            return False
        
    def __load_and_split_docs(self, file_path: str):
        loader = TextLoader(file_path)
        documents = loader.load()
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        return splitter.split_documents(documents)
    
    def __create_tool_from_docs(self, docs, data_type: TableRegistry):
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
            client=supabase_client,
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
        
    
 