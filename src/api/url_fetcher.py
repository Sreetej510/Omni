"""URL content fetching with error handling."""
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import time


class URLFetcher:
    """Fetch content from URLs with proper headers and error handling."""
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 2,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        })
    
    def fetch(self, url: str, fetch_content: bool = True) -> Dict[str, Any]:
        """
        Fetch content from a URL.
        
        Args:
            url: URL to fetch
            fetch_content: Whether to fetch full HTML content
            
        Returns:
            Dictionary with url, status, content, content_type, and error info
        """
        result = {
            "url": url,
            "success": False,
            "content": None,
            "content_type": None,
            "status_code": None,
            "error": None,
            "domain": self._get_domain(url)
        }
        
        # Validate URL
        if not self._is_valid_url(url):
            result["error"] = "Invalid URL format"
            return result
        
        # Try fetching with retries
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                result["status_code"] = response.status_code
                result["content_type"] = response.headers.get("Content-Type", "")
                
                if response.status_code == 200:
                    result["success"] = True
                    if fetch_content:
                        result["content"] = response.text
                    return result
                else:
                    result["error"] = f"HTTP {response.status_code}"
                    
            except requests.exceptions.Timeout:
                result["error"] = "Request timeout"
            except requests.exceptions.ConnectionError:
                result["error"] = "Connection error"
            except requests.exceptions.RequestException as e:
                result["error"] = str(e)
            
            # Wait before retry
            if attempt < self.max_retries:
                time.sleep(1 * (attempt + 1))
        
        return result
    
    def fetch_multiple(self, urls: list, fetch_content: bool = True) -> list:
        """
        Fetch multiple URLs sequentially.
        
        Args:
            urls: List of URLs to fetch
            fetch_content: Whether to fetch full content
            
        Returns:
            List of fetch results
        """
        results = []
        for url in urls:
            result = self.fetch(url, fetch_content)
            results.append(result)
            # Small delay between requests
            time.sleep(0.5)
        return results
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL has valid format."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def _get_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return None
