"""Configuration settings for the simplified multi-agent research system."""
import os
from dotenv import load_dotenv

load_dotenv()

# Brave Search API (Primary search provider)
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

# Model Configuration
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "http://localhost:8016/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "local-model")

# Token Configuration
MAX_COMPLETION_TOKENS = 12000  # Max tokens for all agent turns
MAX_CONTEXT_WINDOW = 262000  # Max total context (prompt + completion)
SUMMARIZATION_THRESHOLD = 0.80  # Trigger summarization at 80% of context window

# State Persistence
STATE_STORAGE_PATH = "research/sessions"
AUTO_SAVE_STATE = True  # Auto-save after each step

# Workspace Configuration
WORKSPACE_ROOT = "research/workspaces"  # Root directory for agent workspaces

# Search Configuration
FETCH_URL_CONTENT = True  # Fetch and clean URL content
HTML_CLEANER = 'beautifulsoup'  # HTML cleaning method
MAX_CONCURRENT_FETCHES = 5  # Maximum concurrent URL fetches

# Brave Search Configuration
BRAVE_MAX_RESULTS_PER_REQUEST = 20  # Max results per API call
BRAVE_DEFAULT_OFFSET = 0  # Starting offset
BRAVE_DEFAULT_FRESHNESS = None  # 'pd', 'pw', 'pm', 'py', or None
BRAVE_DEFAULT_COUNTRY = None  # 2-letter country code
BRAVE_EXTRA_SNIPPETS = False  # Get additional excerpts
BRAVE_SAFE_SEARCH = "moderate"  # 'off', 'moderate', 'strict'
BRAVE_ENABLE_PAGINATION = True  # Enable automatic pagination for more results
BRAVE_DEFAULT_SEARCH_LANG = "en"  # Content language preference

# Quality Configuration
MIN_REFERENCES_DYNAMIC = True  # Dynamic threshold based on topic
MIN_REFERENCES_DEFAULT = 5  # Default minimum per subagent
MIN_CONTENT_LENGTH = 500  # Minimum content length per result
MAX_SINGLE_SOURCE_PERCENTAGE = 0.40  # Max percentage from single domain

# Validation Configuration
VALIDATION_ENABLED = True
MAX_RESEARCH_RETRIES = 3
VALIDATION_SCORE_THRESHOLD = 0.7
