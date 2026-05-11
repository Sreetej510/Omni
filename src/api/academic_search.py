"""Academic search client using OpenAlex API."""
import requests
import time
from typing import List, Dict, Any, Optional
from config.settings import OPENALEX_BASE_URL, OPENALEX_API_KEY


class AcademicSearchClient:
    """
    Wrapper for OpenAlex API to search academic papers.
    
    Features:
    - Search papers by keywords
    - Return paper metadata + PDF URLs
    - Handle rate limiting and errors with automatic retry
    - Free tier: $1/day, or use API key for higher limits
    
    API Details:
    - Base URL: https://api.openalex.org
    - Endpoint: /works?search={keywords}&per_page={max_results}
    - PDF endpoint: /works/{doi_or_id}/pdf
    - API Key: Required for scale (get free key at openalex.org/settings/api)
    
    Free Daily Limits with API Key:
    - List+filter: 10,000 calls (1M results)
    - Search: 1,000 calls (100K results)
    - Content download: 100 calls (100 PDFs)
    - Get single entity: Unlimited
    """
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3):
        """
        Initialize academic search client.
        
        Args:
            api_key: OpenAlex API key (recommended for higher rate limits)
            max_retries: Maximum number of retry attempts for 429 errors
        """
        self.base_url = OPENALEX_BASE_URL or "https://api.openalex.org"
        self.api_key = api_key or OPENALEX_API_KEY
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Set headers
        headers = {
            "User-Agent": "OmniResearchBot/1.0",
            "Accept": "application/json"
        }
        
        # Add API key if available
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.session.headers.update(headers)
    
    def search_papers(
        self,
        query: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for academic papers using OpenAlex semantic search.
        
        Semantic search finds papers by meaning, not just keywords.
        Best for longer queries like abstracts or detailed descriptions.
        
        Args:
            query: Search query (can be short keyword or long description)
            max_results: Number of results (default 50, max 50 per OpenAlex limit)
            
        Returns:
            List of paper dicts with: title, url, pdf_url, authors, abstract, year
        """
        try:
            # OpenAlex semantic search limits to 50 per page
            per_page = min(max_results, 50)
            
            url = f"{self.base_url}/works"
            params = {
                "search.semantic": query,  # Use semantic search
                "per_page": per_page
            }
            
            # Add API key if available
            if self.api_key:
                params["api_key"] = self.api_key
            
            # Retry logic for 429 rate limit errors
            last_error = None
            for attempt in range(self.max_retries):
                response = self.session.get(url, params=params, timeout=30)
                
                # Check if 429 rate limit
                if response.status_code == 429:
                    # Try to get wait time from headers
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                        print(f"[OpenAlex 429] Rate limited. Waiting {wait_time}s (from Retry-After header)...")
                    else:
                        # Default: exponential backoff starting at 15 seconds
                        wait_time = 15 * (2 ** attempt)
                        print(f"[OpenAlex 429] Rate limited (attempt {attempt + 1}/{self.max_retries}). Waiting {wait_time}s...")
                    
                    time.sleep(wait_time)
                    last_error = response
                    continue
                    
                # Success or other error
                response.raise_for_status()
                break
            else:
                # All retries exhausted
                if last_error:
                    print(f"[OpenAlex 429] Max retries ({self.max_retries}) exceeded. Giving up.")
                    print(f"  Status: {last_error.status_code}")
                    print(f"  URL: {last_error.url}")
                    return []
            
            data = response.json()
            results = data.get("results", [])
            
            # Format results
            formatted_results = []
            for paper in results:
                formatted = self._format_paper(paper)
                if formatted:
                    formatted_results.append(formatted)
            
            return formatted_results
            
        except requests.exceptions.Timeout:
            print(f"[OpenAlex Timeout]: Search timed out after 30s")
            return []
        except requests.exceptions.HTTPError as e:
            print(f"[OpenAlex HTTP Error]: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Status: {e.response.status_code}")
                print(f"  URL: {e.response.url}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"[OpenAlex Request Error]: {str(e)}")
            return []
        except Exception as e:
            print(f"[OpenAlex Parse Error]: {str(e)}")
            return []
    
    def _format_paper(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Format paper with essential fields only.
        
        Args:
            paper: Raw paper data from OpenAlex API
            
        Returns:
            Dict with: title, pdf_url, abstract, year, doi
        """
        try:
            # Extract title
            title = paper.get("title", "")
            if not title:
                return None
            
            # Extract DOI
            doi = paper.get("doi")
            
            # Extract PDF URL from open_access
            pdf_url = None
            open_access = paper.get("open_access", {})
            if open_access and open_access.get("is_oa") == True:
                pdf_url = open_access.get("oa_url")
            
            # Extract abstract (reconstruct from inverted index)
            abstract = ""
            abstract_inverted = paper.get("abstract_inverted_index")
            if abstract_inverted:
                try:
                    # Reconstruct abstract from inverted index
                    words_dict = {}
                    for word, positions in abstract_inverted.items():
                        for pos in positions:
                            words_dict[pos] = word
                    
                    # Sort by position and join
                    sorted_words = [words_dict[i] for i in sorted(words_dict.keys())]
                    abstract = " ".join(sorted_words)
                    
                    # Limit abstract length
                    if len(abstract) > 500:
                        abstract = abstract[:500] + "..."
                except Exception:
                    abstract = "Abstract available (detailed text requires full paper fetch)"
            
            # Extract publication year
            year = paper.get("publication_year")
            
            return {
                "title": title,
                "pdf_url": pdf_url,
                "abstract": abstract,
                "year": str(year) if year else "Unknown year",
                "doi": doi
            }
            
        except Exception as e:
            print(f"[Paper Format Error]: {str(e)}")
            return None
    
    def get_pdf_url(self, paper_id: str) -> Optional[str]:
        """
        Get PDF URL for a specific paper.
        
        Args:
            paper_id: OpenAlex paper ID or DOI
            
        Returns:
            PDF URL or None if not available
        """
        try:
            url = f"{self.base_url}/works/{paper_id}"
            
            params = {"select": "open_access"}
            if self.api_key:
                params["api_key"] = self.api_key
            
            # Retry logic for 429 rate limit errors
            last_error = None
            for attempt in range(self.max_retries):
                response = self.session.get(url, params=params, timeout=15)
                
                # Check if 429 rate limit
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                        print(f"[OpenAlex 429] Rate limited. Waiting {wait_time}s...")
                    else:
                        wait_time = 15 * (2 ** attempt)
                        print(f"[OpenAlex 429] Rate limited (attempt {attempt + 1}/{self.max_retries}). Waiting {wait_time}s...")
                    
                    time.sleep(wait_time)
                    last_error = response
                    continue
                
                response.raise_for_status()
                break
            else:
                if last_error:
                    print(f"[OpenAlex 429] Max retries exceeded for PDF URL fetch.")
                    return None
            
            data = response.json()
            open_access = data.get("open_access", {})
            
            if open_access and open_access.get("is_oa") == True:
                return open_access.get("oa_url")
            
            return None
            
        except Exception as e:
            print(f"[OpenAlex PDF URL Error]: {str(e)}")
            return None
    
    def get_paper_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Get paper metadata by DOI.
        
        Args:
            doi: Digital Object Identifier
            
        Returns:
            Formatted paper dict or None
        """
        try:
            url = f"{self.base_url}/works/https://doi.org/{doi}"
            
            params = {}
            if self.api_key:
                params["api_key"] = self.api_key
            
            # Retry logic for 429 rate limit errors
            last_error = None
            for attempt in range(self.max_retries):
                response = self.session.get(url, params=params, timeout=15)
                
                # Check if 429 rate limit
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                        print(f"[OpenAlex 429] Rate limited. Waiting {wait_time}s...")
                    else:
                        wait_time = 15 * (2 ** attempt)
                        print(f"[OpenAlex 429] Rate limited (attempt {attempt + 1}/{self.max_retries}). Waiting {wait_time}s...")
                    
                    time.sleep(wait_time)
                    last_error = response
                    continue
                
                response.raise_for_status()
                break
            else:
                if last_error:
                    print(f"[OpenAlex 429] Max retries exceeded for DOI fetch.")
                    return None
            
            data = response.json()
            return self._format_paper(data)
            
        except Exception as e:
            print(f"[OpenAlex DOI Error]: {str(e)}")
            return None
