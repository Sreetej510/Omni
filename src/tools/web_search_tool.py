"""Web search tool using Brave Search API and OpenAlex academic search."""
from typing import List, Dict, Any, Optional
from src.api.brave_search import BraveSearch
from src.api.academic_search import AcademicSearchClient
from src.utils.url_tracker import URLSourceTracker


class WebSearchTool:
    """
    Web search tool with dual search capability:
    - Brave Search API for general web results
    - OpenAlex API for academic paper results
    - Both searches run on every web_search call
    - URLs tracked with their source for optimal fetching
    """
    
    def __init__(
        self,
        brave_search: Optional[BraveSearch] = None,
        url_tracker: Optional[URLSourceTracker] = None
    ):
        self.brave = brave_search or BraveSearch()
        self.academic = AcademicSearchClient()
        self.url_tracker = url_tracker or URLSourceTracker()
    
    def web_search(
        self,
        query: str,
        freshness: Optional[str] = None
    ) -> str:
        """
        Perform dual search: Brave (web) + OpenAlex (semantic paper search).
        
        Args:
            query: Search query used for BOTH Brave web search AND OpenAlex paper search
            freshness: Time filter for Brave search (pd=past day, pw=past week, pm=past month, py=past year)
            
        Returns:
            Formatted combined search results with both web and paper URLs
        """
        try:
            # Search Brave (general web)
            brave_results = self.brave.search(
                query=query,
                num_results=20,
                freshness=freshness
            )
            
            # Search OpenAlex (semantic paper search) - return all 50 results
            paper_results = self.academic.search_papers(
                query=query,
                max_results=50
            )
            
            # Register all URLs with sources
            self._register_urls(brave_results, paper_results)
            
            # Format and return combined results
            return self._format_combined_results(query, brave_results, paper_results)
            
        except Exception as e:
            return f"Search error: {str(e)}"
    
    def _register_urls(
        self,
        brave_results: List[Dict],
        paper_results: List[Dict]
    ) -> None:
        """
        Register URLs with their source types.
        
        Only tracks:
        - Brave URLs (for regular web fetching)
        - Paper PDF URLs (for direct PDF fetching)
        
        Args:
            brave_results: Results from Brave search
            paper_results: Results from OpenAlex search
        """
        # Register Brave URLs
        for result in brave_results:
            if '_metadata' in result:
                continue
            url = result.get('link') or result.get('url')
            if url:
                self.url_tracker.register_url(url, 'brave')
        
        # Register paper PDF URLs only (not paper pages - they'll use API)
        for paper in paper_results:
            pdf_url = paper.get('pdf_url')
            
            if pdf_url:
                # Track PDF URLs so we know they're academic
                self.url_tracker.register_url(pdf_url, 'openalex_pdf')
    
    def _format_combined_results(
        self,
        query: str,
        brave_results: List[Dict],
        paper_results: List[Dict]
    ) -> str:
        """
        Format combined search results.
        
        Args:
            query: Original search query (used for both Brave and OpenAlex)
            brave_results: Brave search results
            paper_results: OpenAlex search results
            
        Returns:
            Formatted results string
        """
        formatted = []
        
        # Header
        formatted.append(f"Web Search Results for: '{query}'")
        formatted.append("=" * 80)
        formatted.append("")
        
        # Brave results section
        formatted.append("=== General Web Results (Brave) ===")
        brave_count = 0
        
        for i, result in enumerate(brave_results, 1):
            if '_metadata' in result:
                continue
            
            brave_count += 1
            title = result.get('title', 'No title')
            snippet = result.get('snippet', result.get('description', 'No snippet'))
            url = result.get('link', result.get('url', 'No URL'))
            
            formatted.append(f"{i}. {title}")
            formatted.append(f"   URL: {url}")
            formatted.append(f"   Source: Web")
            formatted.append(f"   Preview: {snippet[:200]}...")
            formatted.append("")
        
        if brave_count == 0:
            formatted.append("No web results found.")
            formatted.append("")
        
        # Paper results section
        formatted.append("=== Academic Paper Results (OpenAlex) ===")
        paper_count = 0
        
        for i, paper in enumerate(paper_results, 1):
            paper_count += 1
            
            title = paper.get('title', 'No title')
            pdf_url = paper.get('pdf_url')
            abstract = paper.get('abstract', '')
            year = paper.get('year', 'Unknown year')
            doi = paper.get('doi', '')
            
            formatted.append(f"{i}. {title}")
            if pdf_url:
                formatted.append(f"   PDF: {pdf_url}")
            if doi:
                formatted.append(f"   DOI: {doi}")
            formatted.append(f"   Year: {year}")
            if abstract:
                abstract_preview = abstract[:150] if len(abstract) > 150 else abstract
                formatted.append(f"   Abstract: {abstract_preview}")
            formatted.append("")
        
        if paper_count == 0:
            formatted.append("No paper results found.")
            formatted.append("")
        
        # Summary
        formatted.append("=" * 80)
        formatted.append(f"Total: {brave_count} web URLs, {paper_count} paper URLs")
        formatted.append("Use fetch_url to read full content.")
        
        return "\n".join(formatted)
