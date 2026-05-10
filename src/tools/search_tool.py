"""Enhanced search tool using Brave Search API only."""
from typing import List, Dict, Any, Optional
from src.api.brave_search import BraveSearch
from src.api.url_fetcher import URLFetcher
from src.tools.html_cleaner import HTMLCleaner


class SearchResult:
    """Search result with content."""
    
    def __init__(
        self,
        title: str,
        snippet: str,
        link: str,
        source: str = "brave",
        content: Optional[str] = None,
        fetch_success: bool = False
    ):
        self.title = title
        self.snippet = snippet
        self.link = link
        self.source = source
        self.content = content
        self.fetch_success = fetch_success
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "snippet": self.snippet,
            "link": self.link,
            "source": self.source,
            "content": self.content,
            "fetch_success": self.fetch_success
        }
    
    def __repr__(self):
        return f"SearchResult(title={self.title[:50]}...)"


class SearchTool:
    """
    Search tool using Brave Search API:
    - Executes Brave web searches
    - Fetches and cleans URL content
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
    
    def search(
        self,
        query: Optional[str] = None,
        url: Optional[str] = None,
        num_results: int = 10,
        search_type: str = "web",
        fetch_url_content: bool = True,
        offset: int = 0,
        freshness: Optional[str] = None,
        country: Optional[str] = None,
        extra_snippets: bool = False,
        enable_pagination: bool = False
    ) -> str:
        """
        Perform search or fetch URL:
        - If query: Brave search → fetch URLs
        - If url: Direct fetch & clean
        
        Args:
            query: Search query string (use for web search)
            url: Direct URL to fetch (use for specific URLs)
            num_results: Number of results to return (max 20 per request)
            search_type: Type of search (web, news, images) - currently uses web
            fetch_url_content: Whether to fetch and clean URL content directly
            offset: Starting position for pagination (0-based, max 9)
            freshness: Time filter ('pd'=past day, 'pw'=past week, 'pm'=past month, 'py'=past year)
            country: 2-letter country code for regional results
            extra_snippets: Get additional excerpts per result
            enable_pagination: Automatically paginate to get more results
            
        Returns:
            Formatted search results or URL content
        """
        # Direct URL fetch
        if url:
            result = self.fetch_and_clean_url(url)
            return self._format_url_result(url, result)
        
        # Brave search
        if not query:
            raise ValueError("Provide either 'query' or 'url' parameter")
        
        # Execute Brave search with advanced options
        if enable_pagination:
            # Use pagination to get more results
            brave_results = self.brave.search_with_pagination(
                query=query,
                total_results=num_results,
                freshness=freshness
            )
        else:
            # Single request with offset
            brave_results = self.brave.search(
                query,
                num_results,
                offset=offset,
                freshness=freshness,
                country=country,
                extra_snippets=extra_snippets
            )
        
        # Convert to SearchResult objects
        results = self._convert_to_search_results(brave_results)
        
        # Fetch URL content if requested (directly from URLs, not Brave API)
        if fetch_url_content and self.fetch_content:
            results = self._fetch_all_content(results)
        
        # Format results
        return self._format_results(results)
    
    def _convert_to_search_results(self, brave_results: List[Dict]) -> List[SearchResult]:
        """Convert Brave API results to SearchResult objects."""
        results = []
        for result in brave_results:
            search_result = SearchResult(
                title=result.get("title", ""),
                snippet=result.get("snippet", ""),
                link=result.get("link", ""),
                source="brave"
            )
            results.append(search_result)
        return results
    
    def _fetch_all_content(self, results: List[SearchResult]) -> List[SearchResult]:
        """Fetch content from all URLs with concurrency limiting."""
        if not results:
            return results
        
        # Fetch in batches to avoid overwhelming
        batch_size = self.max_concurrent_fetches
        
        for i in range(0, len(results), batch_size):
            batch = results[i:i + batch_size]
            batch = self._fetch_batch(batch)
            # Update results
            for j, result in enumerate(batch):
                results[i + j] = result
            
            # Small delay between batches
            if i + batch_size < len(results):
                import time
                time.sleep(1)
        
        return results
    
    def _fetch_batch(self, results: List[SearchResult]) -> List[SearchResult]:
        """Fetch content from a batch of URLs."""
        for result in results:
            if result.link and result.link != "No link":
                fetched = self.fetch_and_clean_url(result.link)
                result.content = fetched.get("content")
                result.fetch_success = fetched.get("success", False)
        
        return results
    
    def fetch_and_clean_url(self, url: str) -> Dict[str, Any]:
        """
        Fetch URL content and extract clean text.
        
        Args:
            url: URL to fetch
            
        Returns:
            Dictionary with content and metadata
        """
        # Fetch the URL
        fetch_result = self.url_fetcher.fetch(url, fetch_content=True)
        
        if not fetch_result["success"] or not fetch_result["content"]:
            return {
                "url": url,
                "success": False,
                "content": None,
                "error": fetch_result.get("error", "Fetch failed")
            }
        
        # Clean the HTML
        try:
            clean_text = self.html_cleaner.clean_html(fetch_result["content"])
            
            return {
                "url": url,
                "success": True,
                "content": clean_text,
                "domain": fetch_result.get("domain"),
                "length": len(clean_text)
            }
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "content": None,
                "error": f"HTML cleaning failed: {str(e)}"
            }
    
    def _format_results(self, results: List[SearchResult]) -> str:
        """Format search results with content."""
        if not results:
            return "No search results found."
        
        output_parts = []
        
        for i, result in enumerate(results, 1):
            # Basic info
            output_parts.append(f"{i}. [{result.title}]({result.link})")
            output_parts.append(f"   Source: {result.source.title()}")
            output_parts.append(f"   Snippet: {result.snippet}")
            
            # Content if available
            if result.content and result.fetch_success:
                # Include first 300 chars of content
                content_preview = result.content[:300] + "..." if len(result.content) > 300 else result.content
                output_parts.append(f"   Content Preview:\n   {content_preview}")
            
            output_parts.append("")  # Empty line
        
        # Summary
        fetched_count = sum(1 for r in results if r.fetch_success)
        output_parts.append(f"\n---")
        output_parts.append(f"Total results: {len(results)}")
        output_parts.append(f"Content fetched: {fetched_count}/{len(results)}")
        
        return "\n".join(output_parts)
    
    def _format_url_result(self, url: str, fetch_result: Dict[str, Any]) -> str:
        """
        Format a single URL fetch result.
        
        Args:
            url: The URL that was fetched
            fetch_result: Dictionary from fetch_and_clean_url()
            
        Returns:
            Formatted URL content or error message
        """
        if fetch_result["success"]:
            content = fetch_result["content"]
            # Show full content for direct URL fetch
            return f"URL: {url}\n\nDomain: {fetch_result.get('domain', 'Unknown')}\nLength: {fetch_result.get('length', 0)} chars\n\nContent:\n{content}"
        else:
            return f"Failed to fetch URL: {url}\n\nError: {fetch_result.get('error', 'Unknown error')}"
    
    def search_multiple(
        self,
        queries: List[str],
        num_results: int = 5,
        fetch_content: bool = True
    ) -> Dict[str, str]:
        """
        Perform multiple searches and return results by query.
        
        Args:
            queries: List of search queries
            num_results: Number of results per query
            fetch_content: Whether to fetch URL content
            
        Returns:
            Dictionary mapping queries to their results
        """
        results = {}
        for query in queries:
            results[query] = self.search(
                query,
                num_results,
                fetch_url_content=fetch_content
            )
        return results
    
    def search_with_details(
        self,
        query: str,
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Search and return detailed result objects.
        
        Args:
            query: Search query
            num_results: Number of results
            
        Returns:
            List of SearchResult objects
        """
        brave_results = self.brave.search(query, num_results, "web")
        merged = self._convert_to_search_results(brave_results)
        
        if self.fetch_content:
            merged = self._fetch_all_content(merged)
        
        return merged
