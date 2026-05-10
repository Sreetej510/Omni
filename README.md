# Omni - Multi-Agent Research System

An intelligent multi-agent research system that conducts comprehensive topic research using web search, URL fetching, and subagent delegation. Features centralized findings management, PDF support, and incremental report generation.

## Key Features

- **Multi-Agent Architecture**: Main orchestrator with parallel subagent delegation
- **Dual Search Tools**: Web search (Brave API) for URL discovery + URL fetcher for content
- **PDF Support**: Automatic text extraction from PDF documents using PyMuPDF
- **Centralized Findings**: Shared JSON database for all research findings
- **Incremental Reports**: Build extensive multi-section reports (12K tokens per section)
- **Dynamic Tool Access**: Tools restricted based on query limits and iteration counts
- **Context Management**: Automatic summarization at 70-80% of context window
- **Real Token Tracking**: Uses actual prompt_tokens from API responses
- **Balanced Report Format**: Paragraphs for explanations, limited bullet points (3-7 per subsection)

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

## Architecture

```
User Input
    |
    v
Main Agent (Orchestrator)
    ├── Web Search (Brave API, limit 5 queries)
    ├── URL Fetcher (BeautifulSoup + PDF support)
    ├── Subagent Creation (after 3 iterations)
    ├── Findings Manager (shared JSON database)
    └── Report Builder (incremental sections)
    |
    ├──> Subagent 1 (parallel research)
    ├──> Subagent 2 (parallel research)
    └──> Subagent N (parallel research)
    |
    v
Final Report (reports/<title>.md)
```

## Token Configuration

**Completion Tokens**: 12,000 (max tokens per response)  
**Context Window**: 262,000 (total conversation context)  
**Summarization Threshold**: 70-80% (triggers automatic summarization)

The system tracks actual `prompt_tokens` from API responses for precise context management.

## Report Generation

Reports are built incrementally using two tools:

1. **`report_add_section`**: Add sections with hierarchy (levels 1-6)
   - Each section up to 12K tokens
   - Balanced format: paragraphs + limited bullets (3-7 max)
   - Call MANY times to build comprehensive report

2. **`report_finalize`**: Finalize and save complete report
   - Requires short title for filename
   - Saves to `reports/<title>.md`

**Report Format**:
- Paragraphs for detailed explanations
- Bullet points limited to 3-7 per subsection
- Each bullet 1-2 sentences with substance
- All content from research material only (no speculation)

## Search & Content Fetching

### Web Search (Brave API)
- Limited to 5 queries per research session
- Returns 20 results per search
- Used only for URL discovery

### URL Fetching
- Fetches content directly from URLs
- Supports HTML cleaning with BeautifulSoup
- **PDF Support**: Automatic text extraction using PyMuPDF
- Aggressive filtering to extract meaningful content

## Findings Management

All agents share a centralized findings database (`findings_db.json`):

- **`findings_write`**: Save important facts (up to 1000 words each)
- **`findings_list`**: View all finding IDs and titles
- **`findings_read`**: Read specific findings (supports multiple IDs)

Findings are used for agent reference only, not included in final reports.

## Agent Workflow

### Main Agent
1. **Preliminary Research**: Web search to discover URLs
2. **Content Fetching**: Read URLs for initial understanding
3. **Subagent Creation**: Delegate subtopics (after 3 iterations)
4. **Parallel Research**: Wait for subagents to complete
5. **Report Building**: Add sections incrementally
6. **Finalization**: Call `report_finalize` with title

### Subagents
1. **Receive Instructions**: Specific subtopic and guidelines
2. **Research**: Web search (limit 3) + URL fetching
3. **Save Findings**: Write important facts to shared database
4. **Return Summary**: Concise Q&A-style report (50-100 lines)
5. **Termination**: Forced at iteration 17-20

## Configuration

Key settings in `config/settings.py`:

```python
# Token Configuration
MAX_COMPLETION_TOKENS = 12000  # Max tokens per response
MAX_CONTEXT_WINDOW = 262000  # Max total context
SUMMARIZATION_THRESHOLD = 0.80  # Trigger summarization at 80%

# Workspace Configuration
WORKSPACE_ROOT = "research/workspaces"  # Agent workspaces
```

## File Structure

```
Omni/
├── main.py                          # CLI entry point
├── requirements.txt                 # Dependencies
├── .env                            # API keys
├── README.md                       # This file
├── PROJECT_SUMMARY.md             # Detailed project info
│
├── config/
│   └── settings.py                # Configuration
│
├── src/
│   ├── main_agent.py              # Main orchestrator
│   ├── subagent.py                # Subagent class
│   ├── summarizer_agent.py        # Context summarization
│   │
│   ├── api/
│   │   ├── model_client.py        # LLM API client
│   │   ├── url_fetcher.py         # URL fetching
│   │   └── brave_search.py        # (separate web search tool)
│   │
│   ├── tools/
│   │   ├── web_search_tool.py     # Brave web search
│   │   ├── fetch_url_tool.py      # URL content fetching + PDF
│   │   ├── html_cleaner.py        # HTML text extraction
│   │   ├── findings_manager.py    # JSON findings database
│   │   ├── findings_tools.py      # Findings read/write tools
│   │   └── report_tool.py         # Report generation
│   │
│   └── utils/
│       ├── token_tracker.py       # Token tracking
│       ├── state_manager.py       # State persistence
│       └── tool_validator.py      # Dynamic tool access
│
├── reports/                        # Final reports output
│   └── <title>.md                 # Generated reports
│
└── research/                       # Research storage
    └── workspaces/                # Agent workspaces
        └── main_agent_<id>/       # Main agent workspace
            └── findings_db.json   # Shared findings
```

## Dependencies

```
requests>=2.31.0
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
PyMuPDF>=1.24.0  # PDF text extraction
```

## Brave Search API

- **Endpoint**: `https://api.search.brware.com/res/v1/web/search`
- **Free Tier**: 2,000 requests/month
- **Authentication**: `X-Subscription-Token` header
- **Results**: 20 per request (no pagination needed)

Get API key: https://brave.com/search/api/

## Report Quality Guidelines

The system enforces these quality standards:

1. **Research-Based**: All content from research material only
2. **No Speculation**: Model knowledge not included
3. **Balanced Format**: Paragraphs + limited bullets
4. **Meaningful Content**: No filler or verbose bullet points
5. **Structured Hierarchy**: Levels 1-6 for organization
6. **Concise Subagents**: Q&A-style summaries only

## Benefits

1. **Comprehensive Research**: Multiple subagents for deep coverage
2. **Efficient Search**: Minimal Brave API usage (URL-focused)
3. **PDF Support**: Extract text from academic papers
4. **Context Management**: Automatic summarization prevents overflow
5. **Incremental Reports**: Build extensive reports section-by-section
6. **Quality Control**: Dynamic tool restrictions enforce best practices
7. **Centralized Findings**: Shared knowledge across all agents

## Version History

**Current Version**: Multi-Agent System with Incremental Reports  
**Latest Updates**:
- PDF text extraction support (PyMuPDF)
- Balanced report format (paragraphs + limited bullets)
- 12K token completion limit
- Reports saved to `reports/<title>.md`
- Findings excluded from final reports
- All content from research material only

---

**License**: This project is provided as-is for research and development purposes.
