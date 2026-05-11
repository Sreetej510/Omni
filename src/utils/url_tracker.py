"""URL source tracker for tracking URL origins (Brave vs OpenAlex)."""
import threading
from typing import Dict, Optional


class URLSourceTracker:
    """
    Track URL sources to determine optimal fetch method.
    
    Features:
    - Store mapping: URL -> source type (brave/openalex/openalex_pdf)
    - Thread-safe operations
    - Automatic cleanup of old entries
    """
    
    def __init__(self, max_entries: int = 1000):
        """
        Initialize URL source tracker.
        
        Args:
            max_entries: Maximum number of URLs to track (default 1000)
        """
        self.url_sources: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.max_entries = max_entries
    
    def register_url(self, url: str, source: str) -> None:
        """
        Register URL with its source type.
        
        Args:
            url: The URL to register
            source: Source type ('brave', 'openalex', or 'openalex_pdf')
        """
        with self.lock:
            # Clean up if at capacity
            if len(self.url_sources) >= self.max_entries:
                # Remove oldest 10% of entries
                keys_to_remove = list(self.url_sources.keys())[:len(self.url_sources) // 10]
                for key in keys_to_remove:
                    del self.url_sources[key]
            
            self.url_sources[url] = source
    
    def get_source(self, url: str) -> Optional[str]:
        """
        Get source type for URL.
        
        Args:
            url: The URL to look up
            
        Returns:
            Source type string or None if not found
        """
        with self.lock:
            return self.url_sources.get(url)
    
    def is_paper_url(self, url: str) -> bool:
        """
        Check if URL is from academic source.
        
        Args:
            url: The URL to check
            
        Returns:
            True if URL is from OpenAlex or is a PDF
        """
        source = self.get_source(url)
        if source:
            return source in ['openalex', 'openalex_pdf']
        
        # Fallback: check if URL ends with .pdf
        return url.lower().endswith('.pdf')
    
    def is_brave_url(self, url: str) -> bool:
        """
        Check if URL is from Brave search.
        
        Args:
            url: The URL to check
            
        Returns:
            True if URL is from Brave
        """
        source = self.get_source(url)
        return source == 'brave'
    
    def clear(self) -> None:
        """Clear all tracked URLs."""
        with self.lock:
            self.url_sources.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get tracking statistics.
        
        Returns:
            Dictionary with counts by source type
        """
        with self.lock:
            stats = {'brave': 0, 'openalex': 0, 'openalex_pdf': 0, 'unknown': 0}
            for source in self.url_sources.values():
                if source in stats:
                    stats[source] += 1
                else:
                    stats['unknown'] += 1
            return stats
