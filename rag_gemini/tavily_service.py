import os
from tavily import TavilyClient

class TavilyService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            # We don't raise error immediately to allow app to start if key is missing
            print("Warning: TAVILY_API_KEY is not set. Search functionality will be disabled.")
            self.client = None
        else:
            self.client = TavilyClient(api_key=self.api_key)

    async def search(self, query: str, search_depth: str = "basic", max_results: int = 5) -> dict:
        """
        Performs a search using Tavily API.
        """
        if not self.client:
            raise ValueError("Tavily API key is not configured.")
        
        # Tavily python client is sync, but we can wrap it or just call it.
        # For high concurrency, running in executor is better, but for now direct call is fine.
        try:
            response = self.client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results
            )
            return response
        except Exception as e:
            print(f"Error searching with Tavily: {e}")
            raise

    async def get_search_context(self, query: str, search_depth: str = "basic", max_tokens: int = 4000) -> str:
        """
        Gets a context string from search results suitable for LLM context.
        """
        if not self.client:
            raise ValueError("Tavily API key is not configured.")

        try:
            context = self.client.get_search_context(
                query=query,
                search_depth=search_depth,
                max_tokens=max_tokens
            )
            return context
        except Exception as e:
            print(f"Error getting search context with Tavily: {e}")
            raise
