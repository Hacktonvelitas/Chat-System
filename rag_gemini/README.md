# Gemini RAG System

This is a lightweight RAG (Retrieval-Augmented Generation) system built using `LangChain` and Google's Gemini API. It uses `PGVector` for vector storage and supports PDF, Docx, Excel, and Text files.

## Features
- **Ingestion**: Upload PDF, Docx, Images, etc.
- **Chat**: General text query endpoint.
- **API**: JSON structured response endpoint.
- **Gemini Integration**: Uses Gemini 1.5 Flash for generation and text-embedding-004 for embeddings.

## Prerequisites
- Docker
- Google Gemini API Key

## Setup & Run

1. **Configuration**
   Copy `.env` template and fill in your keys:
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

2. **Build and Run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

   This will start:
   - `rag-app`: The FastAPI application on port 8005.
   - `db`: The PostgreSQL database with `pgvector` on port 5435.

## Usage

### Ingest a Document
```bash
curl -X POST "http://localhost:8005/ingest" -F "file=@/path/to/your/document.pdf"
```

### Batch Ingestion (Folder)
To ingest all files from a directory (e.g., `../documentos`):
```bash
# Ensure the system is running
python ingest_folder.py ../documentos
```

### Chat (Text Response with Memory)
```bash
curl -X POST "http://localhost:8005/chat" \
     -H "Content-Type: application/json" \
     -d '{"text": "What is this document about?", "user_id": "user123"}'
```

### Finalize Chat (Generate Next Steps)
```bash
curl -X POST "http://localhost:8005/finalize?user_id=user123"
```

### API Query (JSON Response)
```bash
curl -X POST "http://localhost:8005/api/query" \
     -H "Content-Type: application/json" \
     -d '{"text": "Summarize the key points.", "mode": "hybrid", "filters": {}}'
```
