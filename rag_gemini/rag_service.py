import os
import shutil
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_postgres import PGVector
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
import pandas as pd

class RAGService:
    def __init__(self, work_dir: str = "./rag_storage"):
        self.work_dir = work_dir
        
        # Ensure GOOGLE_API_KEY is set for LangChain
        if not os.getenv("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        
        # Postgres Connection String
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "rag_user")
        password = os.getenv("POSTGRES_PASSWORD", "rag_password")
        dbname = os.getenv("POSTGRES_DATABASE", "rag_db")
        
        self.connection_string = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        self.collection_name = "rag_documents"
        
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=self.collection_name,
            connection=self.connection_string,
            use_jsonb=True,
        )
        
        self._initialized = True # LangChain setup is mostly sync/lazy

    async def initialize(self):
        # No specific async init needed for LangChain PGVector usually, 
        # but we keep method for compatibility with app.py calls
        pass

    async def ingest_file(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        documents = []
        
        try:
            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
                documents = loader.load()
            elif ext in [".docx", ".doc"]:
                loader = Docx2txtLoader(file_path)
                documents = loader.load()
            elif ext in [".xlsx", ".xls"]:
                # Lightweight Excel loading using pandas
                df = pd.read_excel(file_path)
                # Convert each row to a document
                for _, row in df.iterrows():
                    content = "\n".join([f"{k}: {v}" for k, v in row.items() if pd.notna(v)])
                    documents.append(Document(page_content=content, metadata={"source": file_path}))
            elif ext == ".csv":
                loader = CSVLoader(file_path)
                documents = loader.load()
            elif ext in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                documents = [Document(page_content=content, metadata={"source": file_path})]
            else:
                print(f"Unsupported extension: {ext}")
                return

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(documents)
            
            # Add to vector store
            self.vector_store.add_documents(splits)
            print(f"Ingested {len(splits)} chunks from {file_path}")
            
        except Exception as e:
            print(f"Error ingesting {file_path}: {e}")
            raise

    async def query(self, text: str, mode: str = "hybrid", filters: dict = None) -> str:
        # Construct retriever with filters if provided
        # PGVector supports metadata filtering
        search_kwargs = {"k": 5}
        if filters:
            search_kwargs["filter"] = filters

        retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs)
        
        # Simple RetrievalQA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=False
        )
        
        # Run query synchronously (blocking) as PGVector with psycopg2 is sync
        result = qa_chain.invoke({"query": text})
        return result["result"]

    async def query_json(self, text: str, mode: str = "hybrid", filters: dict = None) -> dict:
        search_kwargs = {"k": 5}
        if filters:
            search_kwargs["filter"] = filters

        retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs)
        
        # We want source documents here
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        
        result = qa_chain.invoke({"query": text})
        
        answer = result["result"]
        source_docs = result.get("source_documents", [])
        
        sources = []
        for doc in source_docs:
            sources.append({
                "content": doc.page_content[:200] + "...",
                "metadata": doc.metadata
            })
            
        return {
            "query": text,
            "answer": answer,
            "sources": sources,
            "filters": filters
        }
