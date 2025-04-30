from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from utils.supabase import supabase_client
from utils.supabase import TableRegistry
from utils.logger import Logger
from pydantic import BaseModel
import os

class MetaDataSchema(BaseModel):
    id: str
    source: str # [File, Model Response, Human Input]
    source_id: str # if source from File, save filename, else if Human Input save user id
    
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
        Mengatur pengetahuan dengan memuat dan membagi dokumen dari direktori yang ditentukan.
        Fungsi ini akan mencari semua file dalam direktori yang ditentukan, memuat konten file tersebut,
        dan kemudian membagi konten menjadi bagian-bagian yang lebih kecil untuk diproses lebih lanjut.
        Dokumen yang dihasilkan kemudian akan disimpan dalam basis data yang sesuai dengan tipe data yang ditentukan.

        Args:
            data_dir (str): Direktori tempat file-file data berada.
            data_type (TableRegistry): Tipe data yang akan digunakan untuk menyimpan pengetahuan.
        """
        try:
            for file in os.listdir(data_dir):
                path = os.path.join(data_dir, file)
                if os.path.isfile(path):
                    self.logger.debug(f"File yang ditemukan: {file}")
                    docs = self.__load_and_split_docs(path)
                    self.saveDataDoc(docs, data_type)
        except Exception as e:
            self.logger.error(f"Error saat menyiapkan pengetahuan: {e}")       
       
    def saveData(self, query: str, meta_data: MetaDataSchema, data_type: TableRegistry) -> None:
        """
        Menyimpan data baru ke basis data yang sesuai dengan tipe data yang ditentukan.
        Fungsi ini akan membagi kueri menjadi bagian-bagian yang lebih kecil, mencari dokumen yang mirip,
        dan kemudian menyimpan kueri baru jika tidak ditemukan dokumen yang sangat mirip.

        Args:
            query (str): Kueri yang akan disimpan.
            meta_data (MetaDataSchema): Metadata yang terkait dengan kueri.
            data_type (TableRegistry): Tipe data yang akan digunakan untuk menyimpan data.
        """
        try:
            self.logger.info("Retrieving vector store for data type...")
            store: SupabaseVectorStore = self.databases[data_type]
            queries = self.__text_spliter(query)

            for q in queries:
                self.logger.info(f"Searching for similar queries: {q[:50]}...")

                results = store.similarity_search_with_relevance_scores(
                    query=q,
                    k=10,
                    score_threshold=0.2
                )

                results.sort(key=lambda x: x[1], reverse=True)

                if results and results[0][1] > 0.7:
                    self.logger.info("Document with >70% similarity found. Skipping save.")
                    continue
                elif len([r for r in results if r[1] > 0.5]) >= 2:
                    self.logger.info("At least 2 documents >50% similarity found. Skipping save.")
                    continue
                elif len([r for r in results if r[1] > 0.33]) >= 3:
                    self.logger.info("At least 3 documents >33% similarity found. Skipping save.")
                    continue
                else:
                    self.logger.info("No highly similar documents found. Saving document...")
                    store.add_texts(texts=[q], metadatas=[meta_data])

        except Exception as e:
            self.logger.error(f"Error adding knowledge: {e}")

    
    def saveDataDoc(self, docs: list[Document], data_type: TableRegistry) -> None:
        """
        Menyimpan dokumen ke basis data yang sesuai dengan tipe data yang ditentukan.
        Fungsi ini akan mencari dokumen yang mirip untuk setiap dokumen yang diberikan,
        dan kemudian menyimpan dokumen baru jika tidak ditemukan dokumen yang sangat mirip.

        Args:
            docs (list[Document]): Daftar dokumen yang akan disimpan.
            data_type (TableRegistry): Tipe data yang akan digunakan untuk menyimpan dokumen.
        """
        try:
            self.logger.info("Retrieving vector store for data type...")
            store: SupabaseVectorStore = self.databases[data_type]

            for doc in docs:
                self.logger.info(f"Checking similarity for document: {doc.page_content[:50]}...")

                results = store.similarity_search_with_relevance_scores(
                    query=doc.page_content,
                    k=10,  # ambil banyak, nanti disaring manual
                    score_threshold=0.2
                )

                # Urutkan berdasarkan skor tertinggi
                results.sort(key=lambda x: x[1], reverse=True)

                # Implementasikan logika pengecekan
                if results and results[0][1] > 0.7:
                    self.logger.info("Document with >70% similarity found. Skipping save.")
                    continue
                elif len([r for r in results if r[1] > 0.5]) >= 2:
                    self.logger.info("At least 2 documents >50% similarity found. Skipping save.")
                    continue
                elif len([r for r in results if r[1] > 0.33]) >= 3:
                    self.logger.info("At least 3 documents >33% similarity found. Skipping save.")
                    continue
                else:
                    self.logger.info("No highly similar documents found. Saving document...")
                    store.add_texts(texts=[doc.page_content], metadatas=[doc.metadata])

        except Exception as e:
            self.logger.error(f"Error saat menambahkan pengetahuan: {e}")


    def loadData(self, query: str, data_type: TableRegistry):
        """
        Memuat data yang sesuai dengan kueri yang diberikan dari basis data yang sesuai dengan tipe data yang ditentukan.
        Fungsi ini akan mencari dokumen yang mirip dengan kueri, mengurutkan hasil berdasarkan skor kesamaan,
        dan kemudian mengembalikan dokumen yang paling mirip.

        Args:
            query (str): Kueri yang akan digunakan untuk memuat data.
            data_type (TableRegistry): Tipe data yang akan digunakan untuk memuat data.

        Returns:
            list: Daftar dokumen yang paling mirip dengan kueri.
        """
        try:
            self.logger.info("Attempting to load data for data type...")
            store: SupabaseVectorStore = self.databases[data_type]

            # Step 1: Search with wider net
            self.logger.info("Performing initial similarity search...")
            results = store.similarity_search_with_relevance_scores(
                query=query,
                k=10,  # cari banyak dulu, nanti kita filter manual
                score_threshold=0.2  # minimal 20% aja biar banyak yang ketangkep
            )

            if not results:
                self.logger.warning("No results found.")
                return []

            # Step 2: Sort results by similarity descending
            results.sort(key=lambda x: x[1], reverse=True)

            # Step 3: Apply your logic
            top_docs = []
            if results[0][1] >= 0.7:
                self.logger.info("Found high similarity > 80%, returning top 1 result.")
                top_docs = results[:1]
            elif any(score >= 0.5 for _, score in results):
                self.logger.info("Found medium similarity > 50%, returning top 2 results.")
                top_docs = [res for res in results if res[1] >= 0.5][:2]
            elif any(score >= 0.33 for _, score in results):
                self.logger.info("Found low similarity > 33%, returning top 3 results.")
                top_docs = [res for res in results if res[1] >= 0.33][:3]
            else:
                self.logger.info("No results passed the thresholds, returning empty.")
                top_docs = []

            self.logger.info(f"Data loaded successfully. Retrieved {len(top_docs)} document(s).")
            return top_docs

        except Exception as e:
            self.logger.error(f"Error loading knowledge: {e}")
            return []

        
    def __load_and_split_docs(self, file_path: str, chunk_size=350):
        self.logger.info("Loading documents from file...")
        loader = TextLoader(file_path)
        documents = loader.load()
        self.logger.info("Splitting documents into smaller chunks...")
        splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=50)
        return splitter.split_documents(documents)
    
    def __text_spliter(self, text: str, chunk_size=350):
        self.logger.info("Splitting text into smaller chunks...")
        splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=50)
        return splitter.split_text(text)
    
       
 