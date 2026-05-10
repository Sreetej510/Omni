# Omni Multi-Agent Research System - Implementation Complete

## Overview

An intelligent multi-agent research system that conducts comprehensive topic research through subagent delegation, web search, and URL fetching. Features centralized findings management, PDF support, and incremental report generation with balanced formatting.

## Core Architecture

- **Main Agent**: Orchestrates research, creates subagents, builds final report
- **Subagents**: Parallel research workers for subtopic delegation
- **Findings Manager**: Shared JSON database for all research findings
- **Dual Search Tools**: Web search (Brave) + URL fetcher (BeautifulSoup + PDF)
- **Report Builder**: Incremental section-based report generation

## Latest Updates (May 10, 2026)

### PDF Text Extraction Support
- Integrated PyMuPDF for automatic PDF text extraction
- Detects PDF URLs and content-type headers
- Extracts clean text from academic papers and documents
- Handles encrypted/corrupted PDFs gracefully

### Balanced Report Format
- **Paragraphs** for detailed explanations
- **Bullet points** limited to 3-7 per subsection
- Each bullet 1-2 sentences with actual substance
- Prevents both dense paragraphs and excessive bullets

### Report Output Changes
- Reports saved to `reports/<title>.md` (not workspace folders)
- `report_finalize` requires short title parameter
- Findings excluded from final reports (reference only)
- No "Total Findings" metadata in reports

### Content Quality Enforcement
- All report content MUST be from research material
- No model speculations or own knowledge
- System prompts emphasize meaningful, relevant content only
- 12K token limit per section

## System Components

### 1. Main Agent (`src/main_agent.py`)

**Responsibilities**:
- Coordinate overall research process
- Create and manage subagents (unlocked after 3 iterations)
- Build incremental multi-section reports
- Enforce query limits (5 web searches max)
- Manage context window with automatic summarization

**Key Features**:
- Dynamic tool access based on iteration count
- Forced report mode after 20 iterations
- Parallel subagent execution
- Real token tracking from API responses

**Report Tools**:
- `report_add_section`: Add sections (levels 1-6, up to 12K tokens each)
- `report_finalize`: Finalize with title parameter, saves to `reports/<title>.md`

### 2. Subagent (`src/subagent.py`)

**Responsibilities**:
- Research specific subtopics delegated by main agent
- Return concise Q&A-style summaries (50-100 lines)
- Save detailed findings to shared database

**Lifecycle**:
- Created by main agent with specific instructions
- Web search limit: 3 queries
- Forced report at iteration 17
- Tool restriction at iteration 19 (only `generate_report`)
- Hard cap at iteration 20

**Context Management**:
- Max context window: 150,000 tokens
- Summarization threshold: 70%
- Automatic summarization when near limit

### 3. Findings Manager (`src/tools/findings_manager.py`)

**Purpose**: Centralized JSON database for research findings

**Features**:
- Thread-safe operations with locking
- Atomic writes to prevent corruption
- Shared across all agents (main + subagents)
- Stores finding ID, title, content (up to 1000 words)

**File**: `research/workspaces/main_agent_<id>/findings_db.json`

**Tools**:
- `findings_write`: Save important facts
- `findings_list`: View all finding IDs and titles
- `findings_read`: Read specific findings (supports multiple IDs)

### 4. Web Search Tool (`src/tools/web_search_tool.py`)

**Brave API Integration**:
- Limited to 5 queries for main agent, 3 for subagents
- Returns 20 results per search (no pagination)
- Used only for URL discovery
- Dynamic tool removal after query limit

**Features**:
- Freshness filters (pd, pw, pm, py)
- Country targeting
- Language preferences
- Safe search options

### 5. URL Fetcher (`src/tools/fetch_url_tool.py`)

**Content Fetching**:
- Direct URL fetching using requests
- HTML cleaning with BeautifulSoup
- **PDF support** with PyMuPDF text extraction
- Content-Type header detection

**PDF Handling**:
- Detects `.pdf` URLs and `application/pdf` content-type
- Extracts text from all pages
- Applies same cleaning pipeline as HTML
- Returns formatted: `[PDF Content from {url}]\n<extracted text>`

### 6. HTML Cleaner (`src/tools/html_cleaner.py`)

**Text Extraction**:
- Aggressive filtering to remove boilerplate
- Priority content containers (main, article, section)
- Minimum paragraph length enforcement
- Deduplication and repetition removal
- Maximum output length: 2,500 characters

**PDF Support**:
- `clean_pdf_content()` method using PyMuPDF
- Handles encrypted and corrupted PDFs
- Same cleaning pipeline as HTML

### 7. Model Client (`src/api/model_client.py`)

**Token Tracking**:
- Tracks actual `prompt_tokens` from API responses
- No accumulation - only latest context size
- Precise context window management
- 300-second timeout for chat calls

**Key Methods**:
- `get_current_prompt_tokens()`: Returns latest prompt token count
- `check_context_window()`: Validates before API calls

### 8. Tool Validator (`src/utils/tool_validator.py`)

**Dynamic Access Control**:
- Enforces web search query limits
- Restricts tools based on iteration count
- Provides informative error messages
- Changes tool signatures dynamically

### 9. Summarizer Agent (`src/summarizer_agent.py`)

**Context Management**:
- Compresses message history when near limit
- Preserves essential research context
- Triggers at 70-80% of context window
- Resets token counter after summarization

## Configuration

`config/settings.py`:

```python
# Token Configuration
MAX_COMPLETION_TOKENS = 12000  # Max tokens per response
MAX_CONTEXT_WINDOW = 262000  # Max total context
SUMMARIZATION_THRESHOLD = 0.80  # Trigger summarization at 80%

# Workspace Configuration
WORKSPACE_ROOT = "research/workspaces"

# Search Configuration
BRAVE_MAX_RESULTS_PER_REQUEST = 20
HTML_CLEANER = 'beautifulsoup'
```

## Research Workflow

### Main Agent Flow

```
1. Initialize with topic
   ↓
2. Web search (up to 5 queries)
   ↓
3. Fetch URLs for content
   ↓
4. Write findings for important facts
   ↓
5. After iteration 3: Create subagents
   ↓
6. Wait for subagents to complete
   ↓
7. After iteration 20: Report mode
   ↓
8. Add report sections (report_add_section)
   ↓
9. Finalize with title (report_finalize)
   ↓
10. Save to reports/<title>.md
```

### Subagent Flow

```
1. Receive subtopic + instructions
   ↓
2. Web search (up to 3 queries)
   ↓
3. Fetch URLs for content
   ↓
4. Write findings to shared database
   ↓
5. After iteration 17: Force report call
   ↓
6. After iteration 19: Only report tool available
   ↓
7. Return concise Q&A summary
   ↓
8. Terminate
```

## Report Generation

### Incremental Section-Based Approach

**Why Incremental?**
- Allows effectively unlimited report size
- Each section gets 12K token budget
- Model can focus on quality per section
- Prevents timeout on massive generation

**Process**:

1. **`report_add_section`** (non-terminating):
   - Parameters: `title`, `level` (1-6), `content`
   - Adds section to internal list
   - Continue calling until report complete

2. **`report_finalize`** (terminating):
   - Parameter: `title` (short title for filename)
   - Assembles all sections into markdown
   - Saves to `reports/<title>.md`
   - Sets `research_complete = True`

### Report Format Guidelines

**Balanced Structure**:
- **Paragraphs**: For detailed explanations and context
- **Bullet Points**: Limited to 3-7 per subsection
- **Bullet Content**: 1-2 sentences with substance
- **Hierarchy**: Levels 1-6 for organization

**Quality Enforcement**:
- All content from research material only
- No model speculations or prior knowledge
- Meaningful and relevant content only
- No filler or verbose bullet points

**Example Format**:

```markdown
# Main Section Title

Introduction paragraph explaining the topic in detail...

## Subsection

Key points:
- First important point with actual substance
- Second point with relevant details
- Third point with supporting information

Further explanation in paragraph form...
```

## File Structure

```
Omni/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── .env                            # API keys
├── README.md                       # User documentation
├── PROJECT_SUMMARY.md             # This file
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
│   │   └── model_client.py        # LLM API client
│   │
│   ├── tools/
│   │   ├── web_search_tool.py     # Brave web search
│   │   ├── fetch_url_tool.py      # URL fetching + PDF
│   │   ├── html_cleaner.py        # HTML/PDF text extraction
│   │   ├── findings_manager.py    # JSON findings database
│   │   ├── findings_tools.py      # Findings tools
│   │   └── report_tool.py         # Report generation
│   │
│   └── utils/
│       ├── token_tracker.py       # Token tracking
│       ├── state_manager.py       # State persistence
│       └── tool_validator.py      # Dynamic tool access
│
├── reports/                        # Final reports
│   └── <title>.md                 # Generated reports
│
└── research/
    └── workspaces/                # Agent workspaces
        └── main_agent_<id>/
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

## API Integration

### Brave Search API
- **Endpoint**: `https://api.search.brave.com/res/v1/web/search`
- **Free Tier**: 2,000 requests/month
- **Usage**: Web search tool only (URL discovery)
- **Results**: 20 per request

### Local Model Server
- **Endpoint**: `http://localhost:8016/v1`
- **Protocol**: OpenAI-compatible API
- **Timeout**: 300 seconds for chat

## Token Management

### Dual Limits System

**Completion Tokens (12,000)**:
- Maximum tokens per model response
- Controls output length
- Applied to each `report_add_section` call

**Context Window (262,000)**:
- Total conversation context
- Includes all message history
- Triggers summarization at 70-80%

### Tracking Method
- Uses actual `prompt_tokens` from API responses
- No accumulation - tracks current context size only
- Precise context management
- Pre-emptive summarization at 70%, critical at 90%

## Key Features

✅ **Multi-Agent Architecture**: Main agent + parallel subagents  
✅ **PDF Support**: Automatic text extraction from PDFs  
✅ **Centralized Findings**: Shared JSON database  
✅ **Incremental Reports**: Build section-by-section  
✅ **Dynamic Tool Access**: Query limits and iteration-based restrictions  
✅ **Context Management**: Automatic summarization  
✅ **Real Token Tracking**: API-based token counts  
✅ **Balanced Format**: Paragraphs + limited bullets  
✅ **Quality Enforcement**: Research-only content  
✅ **Forced Termination**: Subagents and main agent stop properly  

## Quality Standards

### Report Quality
1. **Research-Based**: All content from fetched material
2. **No Speculation**: Model knowledge excluded
3. **Balanced Format**: Appropriate use of paragraphs and bullets
4. **Meaningful Content**: No filler or verbose points
5. **Proper Structure**: Hierarchical organization

### Research Quality
1. **Comprehensive Coverage**: Multiple subagents for depth
2. **Diverse Sources**: Multiple URLs and findings
3. **Accurate Citations**: Findings tracked with IDs
4. **No Redundancy**: Deduplication of content

## Error Handling

### PDF Errors
- Encrypted PDFs: Clear error message
- Corrupted PDFs: Graceful fallback
- Extraction failures: Return error without crashing

### Search Errors
- API failures: Retry with backoff
- Connection errors: Timeout handling
- Invalid responses: Error messages

### Context Management
- Near limit (70%): Pre-emptive summarization
- Critical (90%): Forced summarization
- Hard limit: Validation before API call

## Testing & Validation

All components tested:
- ✅ PDF text extraction
- ✅ Web search query limits
- ✅ Subagent lifecycle
- ✅ Report generation
- ✅ Findings management
- ✅ Context summarization
- ✅ Tool restrictions

## Usage Examples

### Basic Research
```bash
python main.py "Reinforcement learning for day trading with tick data"
```

### List Sessions
```bash
python main.py --list-sessions
```

### Resume Session
```bash
python main.py --session abc123
```

## Version History

**Current Version**: Multi-Agent System with Incremental Reports  
**Latest Features**:
- PDF text extraction (PyMuPDF)
- Balanced report format
- 12K token completion limit
- Reports to `reports/<title>.md`
- Findings excluded from reports
- Research-only content enforcement

## Next Steps

To use the system:

1. Install dependencies: `pip install -r requirements.txt`
2. Configure Brave API key in `.env`
3. Ensure local model server running at `http://localhost:8016`
4. Run research: `python main.py "Your topic"`
5. View reports in `reports/` folder

---

**Version**: Multi-Agent System  
**Implementation Date**: May 2026  
**Status**: Complete and Production Ready

**Key Achievement**: Comprehensive multi-agent research with PDF support, incremental reports, and quality-enforced balanced formatting.
