# Omni - Multi-Agent Research System

An intelligent multi-agent research system for comprehensive topic research. The main agent coordinates parallel subagents that conduct web research, analyze academic papers, and produce detailed reports.

## Quick Start

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure API keys** in `.env`:
```bash
cp .env.example .env
# Add: BRAVE_SEARCH_API_KEY and OPENALEX_API_KEY
```

3. **Start your local model server** at `http://localhost:8016`

4. **Run research**:
```bash
python main.py "Your research topic here"
```

5. **Find your report** in the `reports/` folder

## How It Works

```
User Topic → Main Agent → Parallel Subagents → Detailed Findings → Final Report
```

The main agent breaks your topic into subtopics and delegates research to parallel subagents. Each subagent searches the web (Brave) and academic papers (OpenAlex), reads PDFs, and saves detailed findings. The main agent then synthesizes everything into a comprehensive report saved as `reports/<title>.md`.

## Key Features

- **Multi-Agent Research**: Parallel subagents for fast, comprehensive coverage
- **Academic Papers**: OpenAlex integration with PDF text extraction
- **Sci-Hub Support**: Auto-routes DOI URLs for paper access
- **Smart Search**: Single query searches both web and academic sources
- **Detailed Reports**: Multi-section reports with research-backed content
- **Centralized Findings**: Shared knowledge base across all agents

## Requirements

- Python 3.9+
- Local LLM server (OpenAI-compatible API)
- API keys: [Brave Search](https://brave.com/search/api/), [OpenAlex](https://openalex.org/settings/api)

## Documentation

For detailed information about the architecture, components, configuration, and internals, see [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md).
