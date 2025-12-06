import os
from mem0 import Memory

class MemoryService:
    def __init__(self):
        # Ensure GOOGLE_API_KEY is set for Mem0/Gemini
        if not os.getenv("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

        # Mem0 configuration
        # We assume Mem0 can pick up GEMINI_API_KEY if we configure it correctly or if it uses litellm.
        # If Mem0 strictly requires OpenAI, we might need to adapt.
        # For now, we'll try to initialize it with basic config.
        # Note: As of my knowledge cutoff, Mem0 might default to OpenAI. 
        # We will try to configure it to use Gemini if possible, or fallback/warn.
        
        # Configuration for Mem0 to use Gemini via LiteLLM (if supported)
        # or we just rely on environment variables.
        
        self.config = {
            "llm": {
                "provider": "gemini",
                "config": {
                    "model": "gemini-2.5-flash",
                    "api_key": os.getenv("GEMINI_API_KEY")
                }
            },
            "embedder": {
                 "provider": "gemini",
                 "config": {
                     "model": "models/text-embedding-004",
                     "api_key": os.getenv("GEMINI_API_KEY")
                 }
            },
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": os.getenv("POSTGRES_HOST", "localhost"),
                    "port": int(os.getenv("POSTGRES_PORT", 5432)),
                    "user": os.getenv("POSTGRES_USER", "rag_user"),
                    "password": os.getenv("POSTGRES_PASSWORD", "rag_password"),
                    "dbname": os.getenv("POSTGRES_DATABASE", "rag_db"),
                }
            }
        }
        
        try:
            self.memory = Memory.from_config(self.config)
            print("Mem0 initialized with Gemini and PGVector.")
        except Exception as e:
            print(f"Failed to initialize Mem0 with config: {e}")
            # Fallback to default (might fail if no OpenAI key)
            try:
                self.memory = Memory()
                print("Mem0 initialized with default config.")
            except Exception as e2:
                print(f"Failed to initialize Mem0 completely: {e2}")
                self.memory = None

    def add(self, text: str, user_id: str = "default_user", metadata: dict = None):
        if self.memory:
            self.memory.add(text, user_id=user_id, metadata=metadata)

    def search(self, query: str, user_id: str = "default_user", limit: int = 5):
        if self.memory:
            return self.memory.search(query, user_id=user_id, limit=limit)
        return []

    def get_all(self, user_id: str = "default_user"):
        if self.memory:
            return self.memory.get_all(user_id=user_id)
        return []
