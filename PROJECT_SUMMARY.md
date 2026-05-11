# Omni Multi-Agent Research System

## Overview

Omni is an intelligent multi-agent research system designed for comprehensive topic research. It uses a **pure coordinator** architecture where the main agent solely delegates research to parallel subagents, who handle all web research, academic paper analysis, and detailed findings collection.

## Core Architecture

### Pure Coordinator Pattern

The system follows strict separation of concerns:

- **Main Agent**: Pure orchestrator - creates subagents, reads findings, writes reports
- **Subagents**: Research workers - handle ALL web search, URL fetching, and findings
- **Findings Manager**: Centralized thread-safe JSON database
- **Search Tools**: Unified Brave (web) + OpenAlex (academic) search

## System Components

### 1. Main Agent (`src/main_agent.py`)

**Role**: Pure coordinator with no web research capabilities

**Available Tools** (all from iteration 1):
- `create_subagent` - Delegate research to subagents
- `add_findings` - Save observations
- `findings_list` - List all findings
- `findings_read` - Read specific findings (single or array)
- `report_add_section` - Add report sections (levels 1-3)
- `report_finalize` - Finalize and save report

**Workflow**:
1. Analyze topic → identify 3-5 distinct subtopics
2. Create subagents in parallel with detailed task instructions
3. Read findings from completed subagents
4. Synthesize findings into multi-section report
5. Call `report_finalize` with title

**Properties**:
- Max iterations: 50 (safety cap)
- No tool call limit (unlimited parallel execution)
- Single unified system prompt
- Automatic context summarization at 70-80%

### 2. Subagent (`src/subagent.py`)

**Role**: Research worker with full search capabilities

**Available Tools**:
- `web_search` - Brave + OpenAlex unified (3 query limit)
- `fetch_url` - HTML/PDF/Sci-Hub fetcher
- `add_findings` - Save detailed findings (up to 1000 words)
- `findings_list` / `findings_read` - Review findings
- `generate_report` - Create extensive final report (terminating)

**Lifecycle**:
- Created by main agent with specific task
- Web search limit: 3 queries
- Force report at iteration 25
- Tool restriction (only `generate_report`) at iteration 29
- Hard cap at iteration 30
- Max 3 tool calls per turn
- Max context: 262K tokens, summarize at 70%

**Detailed Paper Finding Format** (13 points):
For every paper read, subagents create findings with:
1. Title
2. Authors and affiliations
3. Publication details
4. DOI/URL
5. Research problem
6. Methodology
7. Key contributions
8. Results
9. Strengths
10. Limitations
11. Relevance to subtopic
12. Important quotes
13. Code/data links

### 3. Findings Manager (`src/tools/findings_manager.py`)

**Purpose**: Centralized thread-safe JSON database

**Features**:
- `threading.Lock()` for thread-safety
- Atomic writes (`os.replace()`) prevent corruption
- Shared across all agents (main + subagents)
- Up to 1000 words per finding
- Batch operations: `add_findings_batch()`, multi-ID `findings_read`

**File Location**: `research/workspaces/main_agent_<id>/findings_db.json`

### 4. Web Search Tool (`src/tools/web_search_tool.py`)

**Unified Search**: Single `query` parameter searches BOTH:
- **Brave Search** - General web URLs
- **OpenAlex** - Academic papers via semantic search

**OpenAlex Features**:
- Endpoint: `search.semantic` for meaning-based search
- Returns up to 50 papers per search
- Supports long descriptive queries

**Returned Paper Metadata**:
- `title`
- `pdf_url` (if open access)
- `abstract` (reconstructed from inverted index)
- `year`
- `doi`

### 5. Fetch URL Tool (`src/tools/fetch_url_tool.py`)

**Smart Routing**:

```
URL Input
    │
    ├── Is DOI URL? → Convert to Sci-Hub URL → Fetch
    ├── Is .pdf URL? → Direct PDF fetch (PyMuPDF)
    ├── Is academic URL? → Check Content-Type
    │     ├── PDF? → Direct PDF fetch
    │     └── HTML? → Fetch via OpenAlex API
    └── Regular URL → Standard HTML fetch
```

**Detection Methods**:
- `_is_pdf_url()` - Checks `.pdf` extension
- `_check_if_pdf_content()` - HEAD request for `Content-Type: application/pdf`
- `_looks_like_academic_pdf()` - URL patterns (arxiv.org, springer.com, etc.)
- `_is_doi_url()` - DOI pattern detection

**Sci-Hub Integration**:
- Auto-converts DOI URLs to `https://sci-hub.ru/<doi_url>`
- Provides access to paywalled papers

**Batch Fetching**:
- `fetch_urls_batch()` - Up to 5 URLs in parallel using threading
- Combined formatted output

### 6. Academic Search Client (`src/api/academic_search.py`)

**OpenAlex API Wrapper**:
- Semantic search via `search.semantic` endpoint
- Up to 50 results per search
- API key support for higher rate limits

**Rate Limit Handling**:
- Detects 429 (Too Many Requests) errors
- Honors `Retry-After` header if present
- Falls back to exponential backoff (15s, 30s, 60s)
- Retries up to 3 times before giving up

Applied to all methods: `search_papers()`, `get_pdf_url()`, `get_paper_by_doi()`

### 7. HTML Cleaner (`src/tools/html_cleaner.py`)

**Aggressive Filtering**:
- Removes boilerplate (nav, footer, ads, scripts)
- Priority content containers (main, article, section, body)
- Minimum paragraph length filtering
- Boilerplate pattern matching
- Deduplication

**Output Limits**:
- HTML content: 25,000 characters
- PDF content: 100,000 characters

**PDF Support**:
- `clean_pdf_content()` using PyMuPDF
- Handles encrypted/corrupted PDFs gracefully
- Same cleaning pipeline as HTML

### 8. Model Client (`src/api/model_client.py`)

**Token Tracking**:
- Tracks actual `prompt_tokens` from API responses
- No accumulation - tracks current context size only
- 300-second timeout for chat calls
- 3 retry attempts on failures

**Key Method**:
- `get_current_prompt_tokens()` - Returns latest count for precise context management

### 9. Tool Validator (`src/utils/tool_validator.py`)

**Dynamic Access Control**:
- Subagent web search limit: 3 queries
- Returns informative error messages
- Generic signature error when limits exceeded

### 10. Summarizer Agent (`src/summarizer_agent.py`)

**Context Management**:
- Compresses message history when near limit
- Preserves essential research context
- Triggers at 70-80% of context window
- Resets token counter after summarization

## Configuration

`config/settings.py`:

```python
# Token Configuration
MAX_COMPLETION_TOKENS = 12000   # Max tokens per response
MAX_CONTEXT_WINDOW = 262000     # Max total context
SUMMARIZATION_THRESHOLD = 0.80  # Trigger summarization at 80%

# Workspace
WORKSPACE_ROOT = "research/workspaces"

# Model
MODEL_BASE_URL = "http://localhost:8016/v1"

# Search
BRAVE_SEARCH_API_KEY = "..."     # From .env
OPENALEX_API_KEY = "..."         # From .env
OPENALEX_BASE_URL = "https://api.openalex.org"
```

## Research Workflow

### Main Agent Flow

```
1. Receive topic
   ↓
2. Analyze topic → identify subtopics
   ↓
3. Create 3-5 subagents in parallel (with specific tasks)
   ↓
4. Wait for subagents to complete (parallel execution)
   ↓
5. Read findings (findings_list + findings_read)
   ↓
6. Synthesize into multi-section report
   ↓
7. Call report_add_section repeatedly
   ↓
8. Call report_finalize with title
   ↓
9. Save to reports/<title>.md
```

### Subagent Flow

```
1. Receive subtopic + task instructions
   ↓
2. web_search (up to 3 queries) - Brave + OpenAlex
   ↓
3. fetch_url for ALL discovered URLs (batch when possible)
   ↓
4. For EACH paper: Save detailed finding (13-point format)
   ↓
5. Continue researching and saving findings
   ↓
6. At iteration 25: Force report mode
   ↓
7. At iteration 29: Restrict to generate_report only
   ↓
8. Call generate_report with extensive details
   ↓
9. Return extensive report to main agent
```

## Report Generation

### Incremental Section-Based Approach

**Process**:

1. **`report_add_section`** (non-terminating):
   - Parameters: `title`, `level` (1-3), `content`
   - Adds section to internal list
   - Continue calling until report complete

2. **`report_finalize`** (terminating):
   - Parameter: `title` (short title for filename)
   - Assembles all sections into markdown
   - Saves to `reports/<title>.md`
   - Sets `research_complete = True`

### Report Format Guidelines

**Structure**:
- Maximum 5-7 main sections
- Heading levels 1-3 ONLY (no level 4+)
- Each section meaningful and relevant only

**Format**:
- Prefer paragraphs over bullets
- Bullets: 3-5 max per subsection
- Each bullet 1-2 substantive sentences
- Focus on synthesis, not listing every detail

**Quality Enforcement**:
- ALL content from research findings
- NO model speculations or own knowledge
- No filler or verbose bullet points
- Avoid redundant headings

## File Structure

```
Omni/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── .env                            # API keys (gitignored)
├── .env.example                    # API key template
├── README.md                       # User documentation
├── PROJECT_SUMMARY.md             # This file
│
├── config/
│   └── settings.py                # Configuration
│
├── src/
│   ├── main_agent.py              # Pure coordinator
│   ├── subagent.py                # Research worker
│   ├── summarizer_agent.py        # Context summarization
│   │
│   ├── api/
│   │   ├── model_client.py        # LLM API client
│   │   └── academic_search.py     # OpenAlex client (with retry)
│   │
│   ├── tools/
│   │   ├── web_search_tool.py     # Brave + OpenAlex unified
│   │   ├── fetch_url_tool.py      # HTML/PDF/Sci-Hub fetcher
│   │   ├── html_cleaner.py        # HTML/PDF text extraction
│   │   ├── findings_manager.py    # Thread-safe JSON DB
│   │   ├── findings_tools.py      # Findings tool interface
│   │   └── report_tool.py         # Report formatting
│   │
│   └── utils/
│       ├── token_tracker.py       # Token tracking
│       ├── state_manager.py       # State persistence
│       ├── tool_validator.py      # Dynamic tool access
│       └── url_tracker.py         # URL source tracking
│
├── reports/                        # Final reports
│   └── <title>.md                 # Generated reports
│
└── research/
    ├── sessions/                  # Session state files
    └── workspaces/
        └── main_agent_<id>/
            └── findings_db.json   # Shared findings DB
```

## Dependencies

```
requests>=2.31.0
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
PyMuPDF>=1.24.0  # PDF text extraction
```

## API Integration

### Brave Search API
- **Endpoint**: `https://api.search.brave.com/res/v1/web/search`
- **Free Tier**: 2,000 requests/month
- **Used by**: Subagents only (3 queries each)
- **Auth**: `X-Subscription-Token` header
- **Results**: 20 per request

### OpenAlex API
- **Endpoint**: `https://api.openalex.org`
- **Search**: `/works?search.semantic={query}&per_page=50`
- **Auth**: `Authorization: Bearer <key>` + `api_key` query param
- **Rate Limits** (Free tier with API key):
  - List+filter: 10,000 calls/day
  - Search: 1,000 calls/day
  - Content download: 100 calls/day
- **Retry Logic**: Automatic on 429 with Retry-After header

### Sci-Hub
- **URL Pattern**: `https://sci-hub.ru/<doi_url>`
- **Auto-Conversion**: Triggered for any DOI URL
- **Purpose**: Access paywalled papers

### Local Model Server
- **Endpoint**: `http://localhost:8016/v1`
- **Protocol**: OpenAI-compatible API
- **Timeout**: 300 seconds for chat
- **Retries**: 3 attempts on failure

## Token Management

### Dual Limits System

**Completion Tokens (12,000)**:
- Maximum tokens per model response
- Controls output length
- Applied to each call

**Context Window**:
- Main agent: 262,000 tokens
- Subagents: 262,000 tokens
- Triggers summarization at 70-80%

### Tracking Method
- Uses actual `prompt_tokens` from API responses
- No accumulation - tracks current context size only
- Pre-emptive summarization at 70%, critical at 90%

## Capabilities

- **Pure Coordinator Architecture**: Main agent only orchestrates
- **Parallel Subagents**: Multiple subagents research simultaneously
- **Unified Search**: Brave + OpenAlex with single query
- **Sci-Hub Integration**: DOI URLs auto-routed
- **PDF Support**: Automatic text extraction with PyMuPDF
- **Smart PDF Detection**: Multiple detection methods
- **Rate Limit Handling**: 429 retry with Retry-After
- **Batch URL Fetching**: Up to 5 URLs in parallel
- **Detailed Paper Findings**: 13-point format, up to 1000 words
- **Extensive Subagent Reports**: Comprehensive details
- **Centralized Findings**: Thread-safe JSON database
- **Incremental Reports**: Build section-by-section
- **Context Management**: Automatic summarization
- **Real Token Tracking**: API-based token counts
- **Balanced Format**: Paragraphs + limited bullets
- **Quality Enforcement**: Research-only content
- **No Tool Limits**: Main agent has unlimited parallel execution

## Quality Standards

### Report Quality
1. **Research-Based**: All content from fetched material
2. **No Speculation**: Model knowledge excluded
3. **Balanced Format**: Appropriate paragraphs and bullets
4. **Meaningful Content**: No filler points
5. **Proper Structure**: Hierarchical organization (levels 1-3)
6. **Synthesis Focus**: Not just listing details

### Subagent Findings Quality
1. **Detailed Papers**: 13-point format for every paper
2. **Comprehensive**: Up to 1000 words per finding
3. **Immediate Saving**: Save findings as discovered
4. **All Important Data**: Methods, results, comparisons, quotes

## Error Handling

### PDF Errors
- Encrypted PDFs: Clear error message
- Corrupted PDFs: Graceful fallback
- Extraction failures: Return error without crashing

### Search Errors
- **OpenAlex 429**: Auto-retry with Retry-After or exponential backoff
- **API failures**: Retry with backoff (3 attempts)
- **Connection errors**: Timeout handling
- **Invalid responses**: Error messages

### Context Management
- Near limit (70%): Pre-emptive summarization
- Critical (90%): Forced summarization
- Hard limit: Validation before API call

### Findings Database
- Concurrent writes: `threading.Lock()` prevents conflicts
- File corruption: Atomic writes via `os.replace()`
- JSON errors: Graceful recovery with backup

## Usage

### Basic Research
```bash
python main.py "Reinforcement learning for day trading with tick data"
```

### Output Example
```
Initialized research agent session: a1b2c3d4
Max completion tokens: 12000
Max context window: 262000

[Iteration 1/50] Context: 1500/262000 (0.6%)
Model is calling 3 tool(s)...
[Executing 3 subagent(s) in parallel]

[Subagent 1] Creating subagent for: RL_Algorithms
[Subagent 2] Creating subagent for: Tick_Data_Processing
[Subagent 3] Creating subagent for: Optuna_Tuning

[SA a1b2c3d4] Iteration 1/30 | Queries: 0
[SA a1b2c3d4] [Tool] web_search
[SA a1b2c3d4] Query #1: reinforcement learning algorithms day trading
...

Report finalized: 7 sections saved to reports/rl_daytrading_tickdata.md
```

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Configure API keys in `.env`:
   - `BRAVE_SEARCH_API_KEY` (from brave.com/search/api/)
   - `OPENALEX_API_KEY` (from openalex.org/settings/api)
3. Ensure local model server running at `http://localhost:8016`
4. Run research: `python main.py "Your topic"`
5. View reports in `reports/` folder
