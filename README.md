# Simplified Multi-Agent Research System v3

A streamlined single-agent research system with real token tracking, JSON state persistence, and automatic history summarization using Brave Search API.

## Key Features

- **Singleton Agent**: Single agent does all research (no subagents)
- **Real Token Tracking**: Uses actual `usage.total_tokens` from API responses
- **State Persistence**: Saves agent state to JSON for later resumption
- **Automatic Summarization**: Triggers at 80% token capacity
- **Brave Search**: Web search via Brave Search API
- **Configurable Token Limits**: Set max tokens via configuration

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure API keys:
```bash
cp .env.example .env
# Edit .env with your Brave API key
```

3. Ensure your local model server is running at `http://localhost:8016`

## Usage

### Basic Research
```bash
python main.py "Your research topic here"
```

### List Saved Sessions
```bash
python main.py --list-sessions
```

### Resume Session
```bash
python main.py --session <session_id>
```

### With Custom Token Limit
```bash
python main.py "Topic" --max-tokens 4096
```

## Architecture

```
User Input
    |
    v
Main Agent (Singleton)
    ├── Real Token Tracking (from API)
    ├── State Persistence (JSON)
    ├── Automatic Summarization (at 80%)
    └── Direct Research Execution
    |
    v
Brave Search Tool
    |
    v
Research Findings
    |
    v
Final Report + Saved State
```

## Dual Token Limits System

The system implements two separate token limits for better control:

**1. Max Completion Tokens (8192):**
- Maximum tokens the model can **generate** in a single response
- Controls output length per API call
- Prevents overly long responses

**2. Max Context Window (262000):**
- Maximum total tokens (prompt + all completions) in the conversation
- Controls how much conversation history can be maintained
- Prevents exceeding model's context limit

**Token Tracking:**
The system uses real token counts from the API response:

```json
{
  "usage": {
    "prompt_tokens": 1117,
    "completion_tokens": 46,
    "total_tokens": 1163
  }
}
```

**Features:**
- Tracks prompt and completion tokens separately
- Monitors total context window usage
- Triggers summarization at 80% of context window
- Resets counters after summarization
- Validates context before sending requests

**CLI Options:**
```bash
# Set completion tokens limit
python main.py "Topic" --max-completion-tokens 4096

# Set context window limit
python main.py "Topic" --max-context-window 131000

# Use both
python main.py "Topic" -c 8192 -w 262000
```

## State Persistence

Agent state is saved to JSON files:

```
research/sessions/
└── research_session_<uuid>.json
```

## Configuration

Key settings in `config/settings.py`:

```python
# Token Configuration (Dual Limits System)
MAX_COMPLETION_TOKENS = 8192  # Max tokens to generate per response
MAX_CONTEXT_WINDOW = 262000  # Max total context (prompt + completion)
SUMMARIZATION_THRESHOLD = 0.80  # Trigger at 80% of context window

# State Persistence
STATE_STORAGE_PATH = "research/sessions"
AUTO_SAVE_STATE = True

# Search Configuration
BRAVE_API_KEY = "your_api_key"  # Set in .env
```

**Token Limits Explained:**
- **MAX_COMPLETION_TOKENS**: Controls how many tokens the model can generate in a single response (output limit)
- **MAX_CONTEXT_WINDOW**: Controls the total conversation context size (prompt + all responses)
- **SUMMARIZATION_THRESHOLD**: When context reaches 80%, automatic summarization is triggered

## Workflow

1. **Start Research**: User provides topic
2. **Track Tokens**: Real-time monitoring from API
3. **Auto-Summarize**: At 80% capacity
4. **Save State**: After each step
5. **Generate Report**: Final comprehensive report
6. **Persist**: Save complete state for resumption

## Dependencies

- requests>=2.31.0
- python-dotenv>=1.0.0
- beautifulsoup4>=4.12.0
- lxml>=4.9.0

## Brave Search API

The system uses Brave Search API for web searches with optimized URL fetching:

### Architecture
- **Phase 1**: Brave API retrieves URLs from search results
- **Phase 2**: Content fetched directly from URLs using `requests` + `BeautifulSoup`
- **Benefit**: Minimizes Brave API calls while maximizing content gathering

### Features

**Pagination:**
- Get more results beyond the initial 20
- Uses `offset` parameter (0-9 max)
- Automatic pagination support via `search_with_pagination()`

**Freshness Filters:**
- `pd`: Past 24 hours
- `pw`: Past 7 days  
- `pm`: Past 31 days
- `py`: Past year
- Custom: Date ranges like `2022-04-01to2022-07-30`

**Advanced Options:**
- **Country Targeting**: 2-letter country codes (e.g., "US", "UK")
- **Language Selection**: Content language preference
- **Extra Snippets**: Up to 5 additional excerpts per result
- **Safe Search**: 'off', 'moderate', 'strict'

**Configuration:**
```python
# config/settings.py
BRAVE_MAX_RESULTS_PER_REQUEST = 20  # Max per API call
BRAVE_DEFAULT_FRESHNESS = None  # 'pd', 'pw', 'pm', 'py', or None
BRAVE_COUNTRY = None  # 2-letter country code
BRAVE_EXTRA_SNIPPETS = False  # Get additional excerpts
BRAVE_ENABLE_PAGINATION = True  # Enable automatic pagination
```

**Usage Examples:**
```python
# Search with freshness filter
results = search_tool.search(
    query="AI developments 2026",
    num_results=10,
    freshness="pw"  # Past week
)

# Search with pagination
results = search_tool.search(
    query="machine learning",
    num_results=30,
    enable_pagination=True  # Automatically paginate
)

# Regional search
results = search_tool.search(
    query="UK politics",
    num_results=10,
    country="UK",
    freshness="pm"  # Past month
)
```

**Endpoint**: `https://api.search.brave.com/res/v1/web/search`  
**Authentication**: `X-Subscription-Token` header  
**Free Tier**: 2,000 requests/month

Get your API key at: https://brave.com/search/api/

## Benefits

1. **Simpler**: Single agent, no delegation
2. **Accurate**: Real token tracking from API
3. **Persistent**: Save and resume sessions
4. **Automatic**: Summarization when needed
5. **Predictable**: Single conversation thread

## v3 Features

✅ **Singleton Agent**: Single agent, no subagents  
✅ **Real Token Tracking**: API-based token counts  
✅ **State Persistence**: Full JSON state saving  
✅ **Auto Summarization**: At 80% capacity  
✅ **Session Resume**: Load and continue sessions  
✅ **Brave Search**: Web search integration  

## License

This project is provided as-is for research and development purposes.
