"""HTML content cleaning using BeautifulSoup to extract text."""
from bs4 import BeautifulSoup
import re
from typing import Optional


class HTMLCleaner:
    """Extract clean text content from HTML pages with aggressive filtering."""
    
    # PDF magic bytes for detection
    PDF_MAGIC_BYTES = b'%PDF-'
    
    # Tags to completely remove
    REMOVE_TAGS = [
        'script', 'style', 'nav', 'header', 'footer', 'aside',
        'form', 'input', 'button', 'select', 'textarea',
        'noscript', 'iframe', 'object', 'embed', 'map',
        'svg', 'canvas', 'video', 'audio', 'source',
        'meta', 'link', 'br', 'hr',
        # Additional noise tags
        'menu', 'sidebar', 'comment', 'author', 'date', 'timestamp',
        'share', 'like', 'follow', 'subscribe',
        'ad', 'advertisement', 'sponsor', 'promo',
        'related', 'popular', 'trending', 'recommended',
        'banner', 'modal', 'tooltip', 'overlay',
        'widget', 'popup', 'overlay'
    ]
    
    # Tags that should preserve their content with spacing
    BLOCK_TAGS = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th']
    
    # Priority content containers - only extract from these if they have significant content
    CONTENT_CONTAINERS = ['main', 'article', 'section', 'content', 'body']
    
    # Patterns to remove from text (boilerplate)
    BOILERPLATE_PATTERNS = [
        r'(?:^|\s)(?:welcome to|learn about|discover|explore)\s+',
        r'(?:click|tap)\s+(?:here|now|below)',
        r'(?:read\s+)?(?:more|full|article|story)',
        r'(?:sign\s+)?(?:up|in|for)',
        r'(?:get\s+)?(?:started|involved)',
        r'(?:don\'t\s+)?miss\s+out',
        r'(?:free\s+)?trial',
        r'(?:limited\s+)?time\s+offer',
        r'subscribe\s+to\s+our',
        r'follow\s+us\s+on',
        r'connect\s+with\s+us',
        r'contact\s+us\s+at',
        r'copyright\s+©?\s*\d{4}',
        r'all\s+rights\s+reserved',
        r'privacy\s+policy',
        r'terms\s+of\s+(?:service|use)',
        r'sitemap',
        r'(?:last\s+)?updated\s+(?:on)?\s*\w+',
        r'(?:view|open)\s+in\s+browser',
        r'forward\s+this\s+email',
        r'unsubscribe',
    ]
    
    # Regular patterns (existing)
    REMOVE_PATTERNS = [
        r'\s+',  # Multiple whitespace
        r'\[.*?\]',  # Bracketed content like [1], [citation]
        r'\(.*?\)',  # Parenthesized content  
        r'https?://[^\s]+',  # URLs
        r'click\s+here',
        r'read\s+more',
        r'sign\s+up',
        r'log\s+in',
        r'share',
        r'print',
        r'email',
    ]
    
    # Configuration for aggressive filtering
    MIN_PARAGRAPH_LENGTH = 25  # Minimum characters per line
    MIN_CONTAINER_LENGTH = 100  # Minimum characters in container to be considered main content
    MAX_OUTPUT_LENGTH = 2500  # Maximum total output length (~400 words)
    
    def clean_html(self, html_content: str) -> str:
        """
        Clean HTML and extract main text content.
        
        Args:
            html_content: Raw HTML string
            
        Returns:
            Cleaned text content
        """
        if not html_content or not html_content.strip():
            return ""
        
        # Check if this is actually PDF content (binary)
        if html_content.startswith('%PDF-') or html_content.strip().startswith('%PDF-'):
            # This is PDF binary data passed as string, try to extract text
            try:
                # Convert back to bytes if it's a string representation
                if isinstance(html_content, str):
                    pdf_bytes = html_content.encode('latin-1')
                else:
                    pdf_bytes = html_content
                return self.clean_pdf_content(pdf_bytes)
            except Exception:
                return ""
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception:
            # Fallback to html.parser if lxml fails
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
            except Exception:
                return ""
        
        # Remove unwanted tags first
        for tag in self.REMOVE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove comments and other elements
        for element in soup.find_all(string=True):
            if isinstance(element, str) and (
                'copyright' in element.lower() or
                'privacy' in element.lower() or
                'terms of use' in element.lower()
            ):
                element.decompose()
        
        # Extract text ONLY from main content containers
        text = self._extract_from_content_containers(soup)
        
        # If no content found in containers, fall back to body
        if not text.strip():
            text = self._extract_from_body(soup)
        
        # Aggressive cleaning pipeline
        text = self._remove_boilerplate(text)
        text = self._filter_meaningful_content(text)
        text = self._remove_repetition(text)
        text = self._clean_text(text)
        text = self._limit_output_length(text)
        
        return text
    
    def clean_pdf_content(self, pdf_bytes: bytes) -> str:
        """
        Extract text content from PDF binary data using PyMuPDF.
        
        Args:
            pdf_bytes: Raw PDF binary data
            
        Returns:
            Extracted text content or error message
        """
        try:
            import fitz  # PyMuPDF
            
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Extract text from all pages
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                if text.strip():
                    text_parts.append(text)
            
            doc.close()
            
            # Combine all text
            full_text = "\n\n".join(text_parts)
            
            if not full_text.strip():
                return ""
            
            # Apply similar cleaning as HTML
            full_text = self._filter_meaningful_content(full_text)
            full_text = self._remove_repetition(full_text)
            full_text = self._clean_text(full_text)
            full_text = self._limit_output_length(full_text)
            
            return full_text
            
        except Exception as e:
            error_msg = str(e).lower()
            if "encrypted" in error_msg or "password" in error_msg:
                return "Error: PDF is encrypted and cannot be processed"
            elif "corrupt" in error_msg or "invalid" in error_msg:
                return "Error: PDF is corrupted or invalid"
            else:
                return f"Error extracting PDF text: {str(e)}"
    
    def _extract_from_content_containers(self, soup: BeautifulSoup) -> str:
        """Extract text only from main content containers (main, article, section, etc.)."""
        texts = []
        
        # Try each container type in priority order
        for container_type in self.CONTENT_CONTAINERS:
            containers = soup.find_all(container_type)
            
            for container in containers:
                # Extract text from this container
                container_text = self._extract_text_from_element(container)
                
                # Only use if it has minimum content
                if len(container_text.strip()) >= self.MIN_CONTAINER_LENGTH:
                    texts.append(container_text)
        
        # Return combined text from all valid containers
        return '\n\n'.join(texts)
    
    def _extract_from_body(self, soup: BeautifulSoup) -> str:
        """Fallback: extract from body if no main containers found."""
        body = soup.find('body')
        if body:
            return self._extract_text_from_element(body)
        
        # Last resort: extract from entire document
        return self._extract_text(soup)
    
    def _extract_text_from_element(self, element) -> str:
        """Extract text from a single element with proper spacing."""
        # Add newlines before block elements
        for tag in self.BLOCK_TAGS:
            for block_elem in element.find_all(tag):
                if block_elem.previous_sibling:
                    block_elem.insert_before('\n')
                if block_elem.next_sibling:
                    block_elem.insert_after('\n')
        
        # Get text
        text = element.get_text(separator=' ')
        
        return text
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract text from BeautifulSoup object with proper spacing."""
        # Add newlines before block elements
        for tag in self.BLOCK_TAGS:
            for element in soup.find_all(tag):
                if element.previous_sibling:
                    element.insert_before('\n')
                if element.next_sibling:
                    element.insert_after('\n')
        
        # Get all text
        text = soup.get_text(separator=' ')
        
        return text
    
    def _remove_boilerplate(self, text: str) -> str:
        """Remove common boilerplate text patterns."""
        if not text:
            return ""
        
        for pattern in self.BOILERPLATE_PATTERNS:
            text = re.sub(pattern, ' ', text, flags=re.I)
        
        # Clean up resulting whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _filter_meaningful_content(self, text: str) -> str:
        """Keep only meaningful paragraphs (minimum length filter)."""
        if not text:
            return ""
        
        lines = text.split('\n')
        
        # Filter out very short lines
        meaningful_lines = []
        for line in lines:
            line = line.strip()
            if len(line) >= self.MIN_PARAGRAPH_LENGTH:
                meaningful_lines.append(line)
        
        return '\n'.join(meaningful_lines)
    
    def _remove_repetition(self, text: str) -> str:
        """Remove repeated lines and content."""
        if not text:
            return ""
        
        lines = text.split('\n')
        seen = set()
        unique_lines = []
        
        for line in lines:
            # Normalize for comparison
            normalized = line.lower().strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    def _limit_output_length(self, text: str) -> str:
        """Limit total output to manageable size."""
        if not text:
            return ""
        
        if len(text) <= self.MAX_OUTPUT_LENGTH:
            return text
        
        # Keep first portion (most important content)
        truncated = text[:self.MAX_OUTPUT_LENGTH]
        # Cut at word boundary
        truncated = truncated.rsplit(' ', 1)[0]
        return truncated + " [... content truncated]"
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing unwanted patterns.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove patterns
        for pattern in self.REMOVE_PATTERNS:
            text = re.sub(pattern, ' ', text, flags=re.I)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        text = '\n'.join(lines)
        
        return text
    
    def clean_html_from_file(self, file_path: str) -> str:
        """
        Clean HTML from a file.
        
        Args:
            file_path: Path to HTML file
            
        Returns:
            Cleaned text content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return self.clean_html(html_content)
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def estimate_content_length(self, text: str) -> int:
        """
        Estimate the meaningful content length.
        
        Args:
            text: Cleaned text
            
        Returns:
            Estimated content length in characters
        """
        if not text:
            return 0
        
        # Remove very short lines (likely navigation/metadata)
        lines = text.split('\n')
        meaningful_lines = [line for line in lines if len(line.strip()) > 20]
        
        return len('\n'.join(meaningful_lines))
