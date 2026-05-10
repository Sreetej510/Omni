"""Web search tool using Brave Search API only."""
from typing import List, Dict, Any, Optional
from src.api.brave_search import BraveSearch
from src.api.url_fetcher import URLFetcher
from src.tools.html_cleaner import HTMLCleaner


class WebSearchTool:
    """
    Web search tool using Brave Search API:
    - Executes Brave web searches
    - Fetches and cleans URL content from search results
    - Returns structured results
    """
    
    def __init__(
        self,
        brave_search: Optional[BraveSearch] = None,
        fetch_content: bool = True,
        max_concurrent_fetches: int = 5
    ):
        self.brave = brave_search or BraveSearch()
        self.fetch_content = fetch_content
        self.max_concurrent_fetches = max_concurrent_fetches
        
        self.url_fetcher = URLFetcher()
        self.html_cleaner = HTMLCleaner()
    
    def web_search(
        self,
        query: str,
        freshness: Optional[str] = None
    ) -> str:
        """
        Perform web search using Brave Search API.
        
        Args:
            query: Search query string
            freshness: Time filter (pd=past day, pw=past week, pm=past month, py=past year)
            
        Returns:
            Formatted search results string with URLs and snippets
        """
        try:
            # Always return 20 results
            results = self.brave.search(
                query=query,
                num_results=20,
                freshness=freshness
            )
            
            if not results or len(results) == 0:
                return "No search results found."
            
            # Format results - these are URLs to investigate further
            formatted_results = []
            formatted_results.append(f"Web Search Results for: '{query}'")
            formatted_results.append(f"Found {len(results)} URLs. Use fetch_url to read full content.\n")
            
            for i, result in enumerate(results, 1):
                # Skip metadata items
                if '_metadata' in result:
                    continue
                    
                title = result.get('title', 'No title')
                snippet = result.get('snippet', result.get('description', 'No snippet'))
                url = result.get('link', result.get('url', 'No URL'))
                
                formatted_results.append(f"{i}. {title}")
                formatted_results.append(f"   URL: {url}")
                formatted_results.append(f"   Preview: {snippet[:200]}...")
                formatted_results.append("")
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"Search error: {str(e)}"
