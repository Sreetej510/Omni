"""URL fetching tool with academic PDF support."""
from typing import Optional, List
import requests
import threading
from src.api.url_fetcher import URLFetcher
from src.api.academic_search import AcademicSearchClient
from src.tools.html_cleaner import HTMLCleaner
from src.utils.url_tracker import URLSourceTracker


class FetchURLTool:
    """
    URL fetching tool with academic paper support:
    - Fetches content from URLs
    - Cleans HTML and extracts text
    - Handles PDF files with text extraction
    - Uses URL source tracker to optimize fetching method
    - Academic PDFs fetched via OpenAlex API when available
    """
    
    def __init__(
        self,
        url_tracker: Optional[URLSourceTracker] = None
    ):
        self.url_fetcher = URLFetcher()
        self.html_cleaner = HTMLCleaner()
        self.url_tracker = url_tracker or URLSourceTracker()
        self.academic_client = AcademicSearchClient()
    
    def _is_pdf_url(self, url: str) -> bool:
        """
        Check if URL appears to be a PDF (by extension only).
        
        Args:
            url: URL to check
            
        Returns:
            True if URL ends with .pdf
        """
        return url.lower().endswith('.pdf')
    
    def _check_if_pdf_content(self, url: str) -> bool:
        """
        Check if URL returns PDF content by making HEAD request.
        
        Args:
            url: URL to check
            
        Returns:
            True if Content-Type indicates PDF
        """
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()
            return 'application/pdf' in content_type
        except Exception:
            return False
    
    def _is_pdf_content(self, content: str, content_type: Optional[str] = None) -> bool:
        """
        Check if content is PDF binary data.
        
        Args:
            content: Raw content string
            content_type: Optional Content-Type header
            
        Returns:
            True if content appears to be PDF
        """
        # Check Content-Type header first
        if content_type and 'application/pdf' in content_type.lower():
            return True
        
        # Check for PDF magic bytes in content
        return content.startswith('%PDF-') or content.strip().startswith('%PDF-')
    
    def _looks_like_academic_pdf(self, url: str) -> bool:
        """
        Check if URL matches common academic PDF patterns.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL matches academic PDF patterns
        """
        academic_patterns = [
            'arxiv.org/pdf',
            'arxiv.org/abs',
            'springer.com/content/pdf',
            'springerlink.com/content/pdf',
            'ieee.org',
            'sciencedirect.com/science/article',
            'wiley.com',
            'tandfonline.com',
            'jstor.org',
            'pubmed.ncbi.nlm.nih.gov',
            'doi.org',  # DOIs often redirect to PDFs
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in academic_patterns)
    
    def _is_doi_url(self, url: str) -> bool:
        """
        Check if URL is a DOI URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is a DOI URL
        """
        doi_patterns = [
            'doi.org/',
            'dx.doi.org/',
            'https://doi.org/',
            'http://doi.org/',
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in doi_patterns)
    
    def _convert_to_scihub_url(self, url: str) -> str:
        """
        Convert DOI URL to Sci-Hub URL for access.
        
        Args:
            url: Original DOI URL
            
        Returns:
            Sci-Hub URL
        """
        # Extract DOI from URL
        doi = url
        if 'doi.org/' in url:
            # Extract everything after doi.org/
            doi = url.split('doi.org/')[-1]
        elif url.startswith('10.'):
            # Already a DOI
            doi = url
        
        # Create Sci-Hub URL
        scihub_url = f"https://sci-hub.ru/{doi}"
        return scihub_url
    
    def fetch_url(self, url: str) -> str:
        """
        Fetch content from a URL using optimal method.
        
        Strategy:
        1. If URL is DOI: Convert to Sci-Hub and fetch
        2. If URL ends with .pdf: Direct fetch
        3. If URL looks like academic PDF (arxiv, springer, etc.): Check Content-Type then direct fetch
        4. Otherwise: Regular HTML fetch
        
        Args:
            url: Direct URL to fetch content from
            
        Returns:
            Cleaned text content or error message
        """
        try:
            # Check URL source
            source = None
            if self.url_tracker:
                source = self.url_tracker.get_source(url)
            
            # Route to appropriate fetch method
            if self._is_doi_url(url):
                # DOI URL - convert to Sci-Hub
                print(f"[Sci-Hub] Converting DOI to Sci-Hub URL: {url}")
                scihub_url = self._convert_to_scihub_url(url)
                print(f"[Sci-Hub] Fetching from: {scihub_url}")
                return self._fetch_regular_url(scihub_url)
            elif self._is_pdf_url(url):
                # Explicit PDF extension - direct fetch
                return self._fetch_pdf_directly(url)
            elif source == 'openalex_pdf':
                # Tracked as academic PDF - check Content-Type first
                if self._check_if_pdf_content(url):
                    return self._fetch_pdf_directly(url)
                else:
                    # Not actually a PDF, fall through to regular fetch
                    return self._fetch_regular_url(url)
            elif self._looks_like_academic_pdf(url):
                # Academic URL pattern (arxiv, springer, ieee, etc.) - check Content-Type
                if self._check_if_pdf_content(url):
                    return self._fetch_pdf_directly(url)
                else:
                    return self._fetch_regular_url(url)
            else:
                # Regular web URL
                return self._fetch_regular_url(url)
            
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"
    
    def _fetch_regular_url(self, url: str) -> str:
        """
        Fetch regular web URL using standard process.
        
        Args:
            url: URL to fetch
            
        Returns:
            Cleaned HTML content
        """
        # Fetch the URL content
        fetch_result = self.url_fetcher.fetch(url)
        
        # Check if fetch was successful
        if not fetch_result.get("success"):
            error_msg = fetch_result.get("error", "Unknown error")
            return f"Error fetching {url}: {error_msg}"
        
        # Extract content and content-type
        html_content = fetch_result.get("content")
        content_type = fetch_result.get("content_type")
        
        if not html_content:
            return f"Error: No content received from {url}"
        
        # Check if this is actually a PDF (even if not tracked)
        if self._is_pdf_content(html_content, content_type):
            if isinstance(html_content, str):
                pdf_bytes = html_content.encode('latin-1')
            else:
                pdf_bytes = html_content
            
            extracted_text = self.html_cleaner.clean_pdf_content(pdf_bytes)
            
            if not extracted_text:
                return f"Error: No text extracted from PDF at {url}"
            
            return f"[PDF Content from {url}]\n{extracted_text}"
        
        # Clean HTML and extract text
        cleaned_text = self.html_cleaner.clean_html(html_content)
        
        if not cleaned_text:
            return f"Error: No content extracted from {url}"
        
        return f"[Content from {url}]\n{cleaned_text}"
    
    def _fetch_pdf_directly(self, url: str) -> str:
        """
        Fetch PDF directly without using OpenAlex API.
        This saves API calls when PDF is directly accessible.
        
        Args:
            url: PDF URL
            
        Returns:
            Extracted PDF text
        """
        try:
            # Direct PDF fetch
            response = requests.get(url, timeout=60)
            
            if response.status_code != 200:
                return f"Error fetching PDF from {url}: HTTP {response.status_code}"
            
            # Check if it's actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
                # Might be HTML error page
                try:
                    text = response.text
                    if '<!DOCTYPE html>' in text or '<html' in text.lower():
                        return f"Error: Received HTML instead of PDF from {url}"
                except:
                    pass
            
            # Process PDF bytes
            pdf_bytes = response.content
            extracted_text = self.html_cleaner.clean_pdf_content(pdf_bytes)
            
            if not extracted_text:
                return f"Error: No text extracted from PDF at {url}"
            
            return f"[PDF Content from {url}]\n{extracted_text}"
            
        except requests.exceptions.Timeout:
            return f"Error: PDF fetch timed out for {url}"
        except Exception as e:
            return f"Error fetching PDF {url}: {str(e)}"
    
    def _fetch_academic_via_api(self, url: str) -> str:
        """
        Fetch academic paper via OpenAlex API (when direct PDF fetch not possible).
        Gets paper metadata and tries to retrieve PDF through API.
        
        Args:
            url: OpenAlex paper URL or DOI
            
        Returns:
            Paper content or metadata
        """
        try:
            # Extract paper ID
            paper_id = self._extract_paper_id(url)
            
            if not paper_id:
                return f"Error: Could not extract paper ID from {url}"
            
            # Get paper metadata from OpenAlex
            paper_data = self.academic_client.get_paper_by_doi(paper_id)
            
            if not paper_data:
                return f"Error: Could not fetch paper metadata for {url}"
            
            # Check if PDF is available
            pdf_url = paper_data.get('pdf_url')
            if pdf_url:
                # Try to fetch PDF directly
                response = requests.get(pdf_url, timeout=60)
                if response.status_code == 200:
                    pdf_bytes = response.content
                    extracted_text = self.html_cleaner.clean_pdf_content(pdf_bytes)
                    
                    if extracted_text:
                        return f"[PDF Content from {url} via OpenAlex]\n{extracted_text}"
            
            # No PDF available, return metadata
            title = paper_data.get('title', 'No title')
            abstract = paper_data.get('abstract', '')
            year = paper_data.get('year', 'Unknown year')
            doi = paper_data.get('doi', '')
            
            metadata = f"[Paper Metadata from {url}]\n"
            metadata += f"Title: {title}\n"
            metadata += f"Year: {year}\n"
            if doi:
                metadata += f"DOI: {doi}\n"
            if abstract:
                metadata += f"\nAbstract:\n{abstract}\n"
            
            return metadata
            
        except Exception as e:
            return f"Error fetching academic paper {url}: {str(e)}"
    
    def _extract_paper_id(self, url: str) -> Optional[str]:
        """
        Extract paper ID from URL.
        
        Args:
            url: Paper URL
            
        Returns:
            Paper ID or None
        """
        # Try to extract DOI
        if 'doi.org' in url:
            parts = url.split('doi.org/')
            if len(parts) > 1:
                return parts[1]
        
        # Try to extract OpenAlex ID
        if 'openalex.org' in url:
            parts = url.split('openalex.org/')
            if len(parts) > 1:
                return parts[1].strip('/')
        
        # Return URL as-is if no pattern matches
        return url
    
    def fetch_urls_batch(self, urls: List[str], max_urls: int = 5) -> str:
        """
        Fetch multiple URLs in parallel (up to max_urls).
        
        Args:
            urls: List of URLs to fetch (max 5)
            max_urls: Maximum number of URLs to process
            
        Returns:
            Combined results from all URLs
        """
        # Limit to max_urls
        urls = urls[:max_urls]
        
        results = {}
        errors = []
        
        def fetch_single(url: str):
            """Fetch a single URL and store result."""
            try:
                result = self.fetch_url(url)
                results[url] = {
                    "success": True,
                    "content": result
                }
            except Exception as e:
                results[url] = {
                    "success": False,
                    "error": str(e)
                }
                errors.append(f"{url}: {str(e)}")
        
        # Create threads for parallel fetching
        threads = []
        for url in urls:
            thread = threading.Thread(target=fetch_single, args=(url,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Format results
        output = []
        success_count = 0
        error_count = 0
        
        for url in urls:
            result = results.get(url, {})
            if result.get("success"):
                success_count += 1
                output.append(f"=== Content from {url} ===\n{result.get('content', '')}")
            else:
                error_count += 1
                output.append(f"=== Error fetching {url} ===\n{result.get('error', 'Unknown error')}")
        
        summary = f"\nBatch complete: {success_count} successful, {error_count} failed out of {len(urls)} URLs"
        return "\n\n---\n\n".join(output) + summary
