"""URL content summarizer for extracting key information."""
import requests
import os
from typing import Optional
from config.settings import MODEL_BASE_URL, MODEL_NAME


class ContentSummarizer:
    """Summarizes fetched URL content to extract only important information."""
    
    def __init__(self):
        # Remove trailing /v1 if present, as we'll add it ourselves
        base_url = MODEL_BASE_URL.rstrip("/v1")
        self.api_url = f"{base_url}/v1/chat/completions"
        self.api_key = os.getenv("MODEL_API_KEY", "not-needed")
        self.model_name = MODEL_NAME
        
    def summarize_content(self, url: str, content: str, max_tokens: int = 2500) -> str:
        """
        Summarize URL content to extract key information.
        
        Args:
            url: Source URL (for context)
            content: Cleaned HTML text content
            max_tokens: Maximum tokens for summary response
            
        Returns:
            Concise summary with only important facts
        """
        # Truncate content if too large (send only first 50K chars)
        truncated_content = content[:50000] if len(content) > 50000 else content
        
        system_prompt = """You are a content extractor. Analyze the provided text and extract ONLY the most important facts, data, and key points. Remove:
- Introduction fluff
- Navigation elements
- Repetitive content  
- Ads, promotions, disclaimers
- Author bios, timestamps
- Related article links
- Social media buttons
- Comments sections

Return only:
- Key facts and statistics
- Important dates and events
- Names of people/organizations involved
- Direct quotes if significant
- Core arguments/conclusions

Be concise but preserve all important information."""
        
        user_prompt = f"""URL: {url}

Extract key information from this content (max {max_tokens} tokens):

{truncated_content}"""
        
        # Make API call with optimized parameters
        try:
            response = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                    "reasoning_effort": "none"
                },
                timeout=600
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"Error summarizing content: HTTP {response.status_code} - {response.text[:200]}"
        except Exception as e:
            return f"Error summarizing content: {str(e)}"
