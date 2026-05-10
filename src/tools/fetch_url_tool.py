"""URL fetching tool for retrieving and cleaning web content."""
from typing import Optional
from src.api.url_fetcher import URLFetcher
from src.tools.html_cleaner import HTMLCleaner


class FetchURLTool:
    """
    URL fetching tool:
    - Fetches content from URLs
    - Cleans HTML and extracts text
    - Handles PDF files with text extraction
    - Returns cleaned text with aggressive filtering
    """
    
    def __init__(self):
        self.url_fetcher = URLFetcher()
        self.html_cleaner = HTMLCleaner()
    
    def _is_pdf_url(self, url: str) -> bool:
        """
        Check if URL points to a PDF file.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to be a PDF
        """
        return url.lower().endswith('.pdf')
    
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
    
    def fetch_url(self, url: str) -> str:
        """
        Fetch content from a URL and clean it.
        
        Args:
            url: Direct URL to fetch content from
            
        Returns:
            Cleaned text content or error message
        """
        try:
            # Fetch the URL content
            fetch_result = self.url_fetcher.fetch(url)
            
            # Check if fetch was successful
            if not fetch_result.get("success"):
                error_msg = fetch_result.get("error", "Unknown error")
                return f"Error fetching {url}: {error_msg}"
            
            # Extract content and content-type from result
            html_content = fetch_result.get("content")
            content_type = fetch_result.get("content_type")
            
            if not html_content:
                return f"Error: No content received from {url}"
            
            # Check if this is a PDF file
            if self._is_pdf_url(url) or self._is_pdf_content(html_content, content_type):
                # Convert string to bytes for PDF processing
                if isinstance(html_content, str):
                    pdf_bytes = html_content.encode('latin-1')
                else:
                    pdf_bytes = html_content
                
                # Extract text from PDF
                extracted_text = self.html_cleaner.clean_pdf_content(pdf_bytes)
                
                if not extracted_text:
                    return f"Error: No text extracted from PDF at {url}"
                
                return f"[PDF Content from {url}]\n{extracted_text}"
            
            # Clean HTML and extract text (regular web page)
            cleaned_text = self.html_cleaner.clean_html(html_content)
            
            if not cleaned_text:
                return f"Error: No content extracted from {url}"
            
            # Return cleaned text directly (no summarization)
            return f"[Content from {url}]\n{cleaned_text}"
            
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"
