"""Enhanced Brave Search API integration with pagination and filters."""
import requests
from typing import List, Dict, Any, Optional
from config.settings import BRAVE_API_KEY


class BraveSearch:
    """Brave Search API client with advanced features."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or BRAVE_API_KEY
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    def is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.api_key)
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        offset: int = 0,
        freshness: Optional[str] = None,
        country: Optional[str] = None,
        search_lang: Optional[str] = None,
        extra_snippets: bool = False,
        safe_search: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """
        Perform a Brave search with advanced options.
        
        Args:
            query: Search query string (1-400 characters, max 50 words)
            num_results: Number of results to return (max 20 per request)
            offset: Starting position for pagination (0-based, max 9)
            freshness: Time filter ('pd'=past day, 'pw'=past week, 'pm'=past month, 'py'=past year)
            country: 2-letter country code for regional results
            search_lang: Content language preference (ISO 639-1)
            extra_snippets: Get up to 5 additional excerpts per result
            safe_search: Content filtering ('off', 'moderate', 'strict')
            
        Returns:
            List of search result dictionaries
        """
        if not self.is_configured():
            return [{
                "title": "Brave Search Not Configured",
                "snippet": f"Brave API key not set. Search query: {query}",
                "link": "",
                "source": "brave"
            }]
        
        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept-Encoding": "gzip",
            "Accept": "application/json"
        }
        
        params = {
            "q": query,
            "count": min(num_results, 20),  # Brave API max is 20
            "offset": min(offset, 9)  # Brave API max offset is 9
        }
        
        # Add optional parameters
        if freshness:
            valid_freshness = ['pd', 'pw', 'pm', 'py']
            if freshness in valid_freshness:
                params["freshness"] = freshness
        
        if country:
            params["country"] = country
        
        if search_lang:
            params["search_lang"] = search_lang
        
        if extra_snippets:
            params["extra_snippets"] = "true"
        
        if safe_search:
            valid_safe_search = ['off', 'moderate', 'strict']
            if safe_search in valid_safe_search:
                params["safesearch"] = safe_search
        
        try:
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            web_results = data.get("web", {}).get("results", [])
            
            for item in web_results:
                result = {
                    "title": item.get("title", ""),
                    "snippet": item.get("description", ""),
                    "link": item.get("url", ""),
                    "source": "brave",
                    "date": item.get("date"),
                    "is_family_friendly": item.get("is_family_friendly")
                }
                
                # Add extra snippets if available
                if extra_snippets and "extra_snippets" in item:
                    result["extra_snippets"] = item.get("extra_snippets", [])
                
                results.append(result)
            
            # Store pagination info
            results_metadata = {
                "more_results_available": data.get("query", {}).get("more_results_available", False),
                "total_results": data.get("web", {}).get("total", 0),
                "offset": offset,
                "count": len(results)
            }
            
            # Attach metadata as special item
            if results:
                results[-1]["_metadata"] = results_metadata
            
            return results
        except requests.exceptions.RequestException as e:
            return [{
                "title": "Brave Search Error",
                "snippet": f"Search failed: {str(e)}. Query: {query}",
                "link": "",
                "source": "brave"
            }]
    
    def search_with_pagination(
        self,
        query: str,
        total_results: int = 20,
        freshness: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform search with automatic pagination to get more results.
        
        Args:
            query: Search query string
            total_results: Desired total number of results (will paginate if needed)
            freshness: Time filter
            
        Returns:
            Combined list of search results from all pages
        """
        all_results = []
        offset = 0
        results_per_page = 20
        
        while len(all_results) < total_results:
            # Get next page
            page_results = self.search(
                query=query,
                num_results=results_per_page,
                offset=offset,
                freshness=freshness
            )
            
            # Check if we got results
            if not page_results or (len(page_results) == 1 and "Error" in page_results[0].get("title", "")):
                break
            
            # Check metadata for more results available
            metadata = None
            for result in page_results:
                if "_metadata" in result:
                    metadata = result.pop("_metadata")
                    break
            
            # Add results (excluding metadata)
            all_results.extend([r for r in page_results if "_metadata" not in r])
            
            # Check if more results available
            if not metadata or not metadata.get("more_results_available", False):
                break
            
            # Move to next page
            offset += 1
        
        return all_results
    
    def get_search_info(self) -> Dict[str, Any]:
        """
        Get information about Brave Search API capabilities.
        
        Returns:
            Dictionary with API information
        """
        return {
            "endpoint": self.base_url,
            "max_results_per_request": 20,
            "max_offset": 9,
            "freshness_options": {
                "pd": "Past 24 hours",
                "pw": "Past 7 days",
                "pm": "Past 31 days",
                "py": "Past year"
            },
            "safe_search_options": ["off", "moderate", "strict"],
            "features": [
                "Pagination",
                "Freshness filtering",
                "Country targeting",
                "Language targeting",
                "Extra snippets",
                "Safe search"
            ]
        }
