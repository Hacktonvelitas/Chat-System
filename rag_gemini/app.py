from __future__ import annotations
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_service import RAGService

from memory_service import MemoryService
from gemini_client import GeminiClient
from tavily_service import TavilyService

def setup_cors(app: FastAPI, allow_all: bool = True) -> None:
    # If ALLOWED_ORIGINS is set, use it.
    if os.getenv("ALLOWED_ORIGINS"):
        origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS").split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return

    # If allow_all is True (default), allow everything.
    if allow_all:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return

    # Fallback defaults for local development if allow_all is False and no env var
    default_origins = [
        "http://localhost", 
        "http://localhost:8080", 
        "http://127.0.0.1", 
        "http://127.0.0.1:8080"
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=default_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app = FastAPI(title="Gemini RAG System", description="Lightweight RAG system using LangChain and Gemini")

setup_cors(app)

# Initialize Services
rag_service = None
tavily_service = None
memory_service = None
gemini_client = None

@app.on_event("startup")
async def startup_event():
    global rag_service, tavily_service, memory_service, gemini_client
    try:
        rag_service = RAGService(work_dir="./rag_storage")
        print("RAG Service initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize RAG Service: {e}")

    try:
        tavily_service = TavilyService()
        print("Tavily Service initialized.")
    except Exception as e:
        print(f"Failed to initialize Tavily Service: {e}")

    try:
        memory_service = MemoryService()
        print("Memory Service initialized.")
    except Exception as e:
        print(f"Failed to initialize Memory Service: {e}")

    try:
        gemini_client = GeminiClient()
    except Exception as e:
        print(f"Failed to initialize Gemini Client: {e}")

class QueryRequest(BaseModel):
    text: str
    mode: str = "hybrid"
    filters: dict = None
    user_id: str = "default_user"

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5
    search_depth: str = "basic"

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG Service not initialized")
    
    if not rag_service._initialized:
        await rag_service.initialize()

    allowed_extensions = {".pdf", ".docx", ".doc", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".md", ".jpg", ".jpeg", ".png", ".bmp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
         pass

    temp_file_path = f"temp_{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        await rag_service.ingest_file(temp_file_path)
        
        return {"message": f"Successfully ingested {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/search")
async def search_endpoint(request: SearchRequest):
    if not tavily_service or not tavily_service.client:
        raise HTTPException(status_code=503, detail="Tavily Service not configured")
    
    try:
        results = await tavily_service.search(request.query, search_depth=request.search_depth, max_results=request.max_results)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_endpoint(request: QueryRequest):
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG Service not initialized")
    
    # Retrieve context from memory
    memory_context = ""
    if memory_service:
        memories = memory_service.search(request.text, user_id=request.user_id)
        if memories:
            memory_context = "\nRelevant Memory:\n" + "\n".join([m['memory'] for m in memories])

    # Append memory to query (simple approach)
    # Or we can pass it as history if LightRAG supports it better.
    # For now, we prepend it to the text.
    augmented_text = f"{memory_context}\nUser Query: {request.text}" if memory_context else request.text
    
    try:
        response = await rag_service.query(augmented_text, mode=request.mode, filters=request.filters)
        
        # Add interaction to memory
        if memory_service:
            memory_service.add(f"User: {request.text}\nAssistant: {response}", user_id=request.user_id)
            
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def json_endpoint(request: QueryRequest):
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG Service not initialized")
    
    try:
        response = await rag_service.query_json(request.text, mode=request.mode, filters=request.filters)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/finalize")
async def finalize_chat(user_id: str = "default_user"):
    """
    Generates a JSON with next steps based on the chat history.
    """
    if not memory_service or not gemini_client:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        # Get all memories for the user
        # Note: get_all might return a lot, we might want to limit or summarize.
        # Mem0's get_all returns list of dicts.
        memories = memory_service.get_all(user_id=user_id)
        history_text = "\n".join([m['memory'] for m in memories])
        
        prompt = f"""
        Based on the following conversation history, generate a JSON object with the following specific structure in Spanish:
        
        History:
        {history_text}
        
        Format:
        {{
            "resumen_conversacion": "Resumen detallado de la conversación",
            "puntos_importantes": [
                "Punto importante 1",
                "Punto importante 2"
            ],
            "pasos_desarrollo": [
                {{
                    "descripcion": "Descripción del paso a seguir",
                    "completado": false
                }},
                {{
                    "descripcion": "Descripción del siguiente paso",
                    "completado": false
                }}
            ]
        }}
        
        Ensure 'completado' is always boolean false.
        """
        
        response_text = await gemini_client.generate_content(
            model_name="gemini-2.5-flash",
            prompt=prompt
        )
        
        # Clean up response to ensure valid JSON (simple heuristic)
        # In production, use structured output or robust parsing.
        import json
        try:
            # Try to find JSON block
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                return {"error": "Could not parse JSON", "raw_response": response_text}
        except Exception:
             return {"error": "Could not parse JSON", "raw_response": response_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
