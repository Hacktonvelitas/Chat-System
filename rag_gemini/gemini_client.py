import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

class GeminiClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        
        genai.configure(api_key=self.api_key)
        
        # Default safety settings
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    async def generate_content(self, model_name: str, prompt: str, system_prompt: str = None, history_messages: list = None, **kwargs):
        """
        Generates content using the specified Gemini model.
        Adapts to the interface expected by RAGAnything/LightRAG.
        """
        model = genai.GenerativeModel(model_name)
        
        messages = []
        if system_prompt:
            # Gemini doesn't have a strict 'system' role in the same way as OpenAI in chat history,
            # but we can prepend it or use system_instruction if supported by the model version.
            # For simplicity and broad compatibility, we'll prepend to the prompt or use system_instruction.
             model = genai.GenerativeModel(model_name, system_instruction=system_prompt)

        chat = model.start_chat(history=[])
        
        # Convert history_messages if needed, but for RAG usually we just need the prompt
        # If history is provided, we might need to adapt it.
        
        try:
            response = await chat.send_message_async(prompt, safety_settings=self.safety_settings, **kwargs)
            return response.text
        except Exception as e:
            print(f"Error generating content with Gemini: {e}")
            raise

    async def embed_content(self, model_name: str, texts: list[str]):
        """
        Generates embeddings for a list of texts.
        """
        try:
            # Gemini embedding model usually 'models/text-embedding-004' or similar
            result = genai.embed_content(
                model=model_name,
                content=texts,
                task_type="retrieval_document" # or retrieval_query depending on usage
            )
            return result['embedding']
        except Exception as e:
            print(f"Error embedding content with Gemini: {e}")
            raise
