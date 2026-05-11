"""Subagent class for delegated research tasks."""
import os
import uuid
from typing import Dict, Any, Optional, List
from src.api.model_client import ModelClient
from src.tools.web_search_tool import WebSearchTool
from src.tools.fetch_url_tool import FetchURLTool
from src.tools.report_tool import ReportTool
from src.tools.file_system_tool import FileSystemTool
from src.tools.findings_manager import FindingsManager
from src.tools.findings_tools import FindingsTools
from src.utils.token_tracker import TokenTracker
from src.utils.tool_validator import ToolValidator
from src.summarizer_agent import SummarizerAgent
from config.settings import MAX_COMPLETION_TOKENS, MAX_CONTEXT_WINDOW, SUMMARIZATION_THRESHOLD


class Subagent:
    """
    Subagent for researching specific subtopics.
    
    Each subagent:
    - Has its own workspace
    - Conducts independent research
    - Tracks its own token usage
    - Saves its findings
    """
    
    def __init__(
        self,
        subtopic: str,
        instructions: str,
        parent_workspace: str,
        model_client: ModelClient,
        web_search_tool: Optional[WebSearchTool] = None,
        fetch_url_tool: Optional[FetchURLTool] = None,
        max_completion_tokens: Optional[int] = None,
        max_context_window: Optional[int] = None
    ):
        """
        Initialize a subagent.
        
        Args:
            subtopic: The subtopic this subagent will research
            instructions: Detailed research instructions
            parent_workspace: Parent agent's workspace directory
            model_client: Model client for LLM interactions
            web_search_tool: Web search tool for Brave searches
            fetch_url_tool: URL fetching tool
            max_completion_tokens: Maximum tokens per response
            max_context_window: Maximum context window size
        """
        self.subtopic = subtopic
        self.instructions = instructions
        self.subagent_id = str(uuid.uuid4())[:8]
        self.parent_workspace = parent_workspace
        
        # Initialize components
        self.max_completion_tokens = max_completion_tokens or MAX_COMPLETION_TOKENS
        # Subagents use the same context window as main agent (262K)
        self.max_context_window = max_context_window or MAX_CONTEXT_WINDOW
        self.model_client = model_client
        self.web_search_tool = web_search_tool or WebSearchTool()
        self.fetch_url_tool = fetch_url_tool or FetchURLTool()
        # Subagents summarize at 70% to leave room for response generation
        self.token_tracker = TokenTracker(self.max_completion_tokens, self.max_context_window, 0.70)
        self.tool_validator = ToolValidator(web_search_limit=3)  # Subagent limit: 3
        self.report_tool = ReportTool(None)
        self.summarizer = SummarizerAgent(model_client)
        
        # Initialize findings manager and tools (shared with parent agent)
        self.findings_manager = FindingsManager(parent_workspace)
        self.findings_tools = FindingsTools(self.findings_manager)
        
        # Message history
        self.message_history: List[Dict[str, str]] = []
        self.research_complete = False
        self.research_findings: Dict[str, Any] = {
            "subtopic": subtopic,
            "instructions": instructions,
            "search_queries": [],
            "findings": [],
            "completed": False
        }
        
        # Initialize with system message
        self.message_history.append({
            "role": "system",
            "content": self._get_system_prompt()
        })
        
        print(f"\n{'='*60}")
        print(f"SUBAGENT CREATED: {self.subagent_id}")
        print(f"Subtopic: {subtopic}")
        print(f"Instructions: {instructions}")
        print(f"{'='*60}\n")
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the subagent."""
        return f"""You are a research assistant. Research: {self.subtopic}

Instructions: {self.instructions}

CRITICAL: Save EVERY important finding using add_findings tool. Be extremely thorough.

AVAILABLE TOOLS:
- web_search: Discover URLs (limit: 3 searches)
- fetch_url: Read content from URLs (read as many as needed!)
- add_findings: Save research findings (MUST use for EVERY important detail!)
- findings_list: List saved findings
- findings_read: Read saved findings
- generate_report: Create extensive final report (TERMINATING)

IMPORTANT RULES:
- Use add_findings for EVERY important fact, detail, statistic, quote, and source
- Save findings IMMEDIATELY after discovering them
- Each finding can be up to 1000 words - use the full capacity!
- Be extremely detailed: save methodology, comparisons, pros/cons, implementation details
- Save ALL relevant URLs, references, and source information
- You can call maximum 3 tools per turn - prioritize add_findings for important discoveries
- generate_report creates an EXTENSIVE report with all important details
- The report should include as many important details as possible

CRITICAL: PAPER/ARTICLE FINDINGS - For EVERY paper or article you read:
- Create a SEPARATE finding for EACH paper/article
- Use as many words as needed (up to 1000) to describe it comprehensively
- Include ALL important details about the paper

PAPER FINDING FORMAT (use this structure for each paper):
1. **Title**: Full paper title
2. **Research Problem**: What problem does this paper address?
3. **Methodology**: Detailed description of methods, algorithms, approaches
4. **Key Contributions**: What new knowledge/methods does this paper provide?
5. **Results**: Quantitative results, performance metrics, comparisons
6. **Strengths**: What makes this paper valuable?
7. **Limitations**: What are the paper's weaknesses or gaps?
8. **Relevance**: How does this relate to the research topic?
9. **Quotes**: Important direct quotes from the paper
10. **Code/Data**: Links to code repositories, datasets if available

WORKFLOW:
1. Use web_search (up to 3 times) to discover relevant URLs and papers
2. Use fetch_url to read content from ALL discovered URLs, especially academic papers
3. For EVERY important relevant paper/article you read, create a DETAILED finding:
   - Title: "Paper: [Paper Title]" or "Article: [Article Title]"
   - Content: Complete detailed analysis using the format above (500-1000 words)
   - Include ALL important information, don't skip details!
4. For other important findings (algorithms, techniques, comparisons), save separate findings
5. Continue researching and saving findings
6. When research is complete, call generate_report with ALL important details included

FINDINGS TO SAVE (examples):
- DETAILED PAPER FINDINGS (MOST IMPORTANT - do this for EVERY important relevant paper!)
- Algorithm descriptions and comparisons
- Performance metrics and statistics
- Implementation approaches and code patterns
- Advantages and disadvantages
- Data preprocessing techniques
- Feature engineering methods
- Trading strategies and approaches
- Risk management techniques
- Library and framework recommendations
- Best practices and recommendations
- Case studies and real-world applications

Call tools - do not just describe them! Be thorough and save EVERYTHING important! For papers, write as many words as needed to capture all important details!"""
    
    def research(self) -> Dict[str, Any]:
        """
        Conduct research on the assigned subtopic.
        
        Returns:
            Dictionary containing research findings
        """
        print(f"[SA {self.subagent_id}] Starting: {self.subtopic[:50]}...")
        
        # Add user message with subtopic
        self.message_history.append({
            "role": "user",
            "content": f"Research your assigned subtopic: {self.subtopic}"
        })
        
        # Research loop with iteration limits
        max_iterations = 30
        force_report_iteration = 25
        restrict_tools_iteration = 29
        iteration = 0
        error_occurred = None
        forced_report = False
        tools_restricted = False
        
        while True:
            iteration += 1
            query_count = len(self.research_findings.get("search_queries", []))
            context_pct = (self.token_tracker.context_tokens / self.max_context_window) * 100
            print(f"[SA {self.subagent_id}] Iteration {iteration}/20 | Queries: {query_count} | Context: {self.token_tracker.context_tokens}/{self.max_context_window} ({context_pct:.1f}%)")
            
            # Force report at iteration >= 17
            if iteration >= force_report_iteration and not forced_report:
                forced_report = True
                print(f"[SA {self.subagent_id}] Forcing report at iteration {iteration}")
                self.message_history.append({
                    "role": "user",
                    "content": f"You have completed {iteration} iterations. Generate your final report NOW using generate_report() with all available data from your research."
                })
            
            # Restrict tools to ONLY generate_report at iteration >= 19
            if iteration >= restrict_tools_iteration and not tools_restricted:
                tools_restricted = True
                print(f"[SA {self.subagent_id}] Restricting tools to generate_report ONLY")
                self.message_history.append({
                    "role": "user",
                    "content": f"CRITICAL: You have only ONE tool available - generate_report. Call it NOW with your complete research findings. No other tools are available."
                })
            
            # Check token limit and summarize if near limit
            if self.token_tracker.is_near_limit():
                print(f"[SA {self.subagent_id}] Summarizing (near token limit)")
                self._summarize_history()
            
            # Call model
            try:
                response = self._call_model(forced_report=forced_report, restrict_tools=tools_restricted)
            except Exception as e:
                error_occurred = f"Model call error: {str(e)}"
                print(f"[Subagent {self.subagent_id}] Error: {error_occurred}")
                break
            
            # Check if research is complete
            if self._is_research_complete(response) or self.research_complete:
                print(f"[Subagent {self.subagent_id}] Research complete")
                self.research_findings["completed"] = True
                break
            
            # Check max iterations
            if iteration >= max_iterations:
                print(f"[SA {self.subagent_id}] Max iterations reached")
                break
        
        # Save final findings
        self._save_findings()
        
        # Print cumulative query summary for subagent
        total_queries = len(self.research_findings.get("search_queries", []))
        web_query_count = sum(1 for q in self.research_findings.get("search_queries", []) if not q.startswith("URL:"))
        
        print(f"[SA {self.subagent_id}] Complete | Queries: {web_query_count} web, {total_queries - web_query_count} URL fetches")
        
        # Return ONLY the report or failure message (not the findings dict)
        try:
            from src.tools.report_agent import ReportAgent
            # Generate concise Q&A style report
            report = self._generate_concise_report(error_occurred)
            
            return report
            
        except Exception as e:
            error_msg = f"Error generating return report: {str(e)}"
            print(f"[Subagent {self.subagent_id}] {error_msg}")
            return error_msg
    
    def _generate_concise_report(self, error_occurred: bool) -> str:
        """
        Generate an extensive, detailed report with all important findings.
        
        This returns a comprehensive report with as many important details as possible.
        All findings are also saved to findings_db.json via add_findings tool.
        
        Args:
            error_occurred: Whether an error occurred during research
            
        Returns:
            Extensive report string with all important details
        """
        if error_occurred:
            return f"ERROR: Subagent failed on subtopic '{self.subtopic}'. Error: {error_occurred}"
        
        # Extract key information
        search_queries = self.research_findings.get("search_queries", [])
        web_queries = [q for q in search_queries if not q.startswith("URL:")]
        url_fetches = [q for q in search_queries if q.startswith("URL:")]
        
        # Build extensive report
        lines = []
        
        # Header
        lines.append(f"# Research Report: {self.subtopic}")
        lines.append("")
        lines.append(f"**Research Instructions:** {self.instructions}")
        lines.append(f"**Total Web Searches:** {len(web_queries)}")
        lines.append(f"**Total URLs Fetched:** {len(url_fetches)}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"This research focused on {self.subtopic}. Conducted comprehensive web research with {len(web_queries)} searches and retrieved detailed content from {len(url_fetches)} URLs. All important findings have been documented below and saved to the findings database.")
        lines.append("")
        
        # Detailed Findings Section
        lines.append("## Detailed Research Findings")
        lines.append("")
        
        # Get all findings from research
        findings = self.research_findings.get("findings", [])
        
        if findings:
            # Group findings by type
            web_findings = [f for f in findings if f.get("search_type") == "Web search"]
            url_findings = [f for f in findings if f.get("search_type") == "fetch_url"]
            
            # Web Search Results
            if web_findings:
                lines.append("### Web Search Discoveries")
                lines.append("")
                for i, finding in enumerate(web_findings, 1):
                    query = finding.get("query", "Unknown query")
                    results = finding.get("results", [])
                    lines.append(f"**Search #{i}:** {query}")
                    lines.append("")
                    if results:
                        for result in results[:10]:  # Show up to 10 results per search
                            if isinstance(result, dict):
                                title = result.get("title", "No title")
                                snippet = result.get("snippet", "")
                                url = result.get("url", "")
                                lines.append(f"- **{title}**")
                                if snippet:
                                    lines.append(f"  - {snippet[:200]}...")
                                if url:
                                    lines.append(f"  - Source: {url}")
                        lines.append("")
            
            # URL Content Results
            if url_findings:
                lines.append("### Fetched URL Content")
                lines.append("")
                for i, finding in enumerate(url_findings, 1):
                    url = finding.get("query", "Unknown URL")
                    content = finding.get("content", "")
                    lines.append(f"**URL #{i}:** {url}")
                    lines.append("")
                    if content:
                        # Truncate very long content but keep substantial details
                        if len(content) > 2000:
                            lines.append(content[:2000] + "... [truncated, see findings database for full content]")
                        else:
                            lines.append(content)
                    lines.append("")
            
            # Additional Findings (from add_findings tool)
            lines.append("### Additional Research Findings")
            lines.append("")
            lines.append("The following detailed findings were saved to the findings database:")
            lines.append("")
            
            # Show summary of all findings
            for i, finding in enumerate(findings, 1):
                title = finding.get("title", f"Finding #{i}")
                search_type = finding.get("search_type", "General research")
                lines.append(f"**{i}. {title}** ({search_type})")
            lines.append("")
        else:
            lines.append("No detailed findings recorded during this research session.")
            lines.append("")
        
        # Key Insights Section
        lines.append("## Key Insights & Conclusions")
        lines.append("")
        lines.append(f"1. **Research Scope:** Comprehensive research conducted on {self.subtopic}")
        lines.append(f"2. **Data Sources:** {len(web_queries)} web searches + {len(url_fetches)} direct URL fetches")
        lines.append("3. **Findings Storage:** All important details saved to findings database for reference")
        lines.append("4. **Coverage:** Multiple aspects explored through diverse search queries and sources")
        lines.append("")
        
        # References Section
        lines.append("## References & Sources")
        lines.append("")
        lines.append("All URLs and sources used in this research:")
        lines.append("")
        
        # Collect unique URLs
        unique_urls = set()
        for finding in findings:
            if finding.get("search_type") == "fetch_url":
                url = finding.get("query", "")
                if url:
                    unique_urls.add(url)
            # Also check results from web searches
            results = finding.get("results", [])
            for result in results:
                if isinstance(result, dict):
                    url = result.get("url", "")
                    if url:
                        unique_urls.add(url)
        
        for i, url in enumerate(unique_urls, 1):
            lines.append(f"{i}. {url}")
        lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append(f"*Report generated by Subagent {self.subagent_id}*")
        lines.append(f"*Research conducted on: {self.subtopic}*")
        
        return "\n".join(lines)
    
    def _summarize_history(self):
        """Summarize message history when approaching token limit."""
        print(f"[Subagent {self.subagent_id}] Current token usage: {self.token_tracker.context_tokens}")
        print(f"[Subagent {self.subagent_id}] Summarizing to free up context...")
        
        # Create summarized history
        summarized = self.summarizer.create_summarized_history(self.message_history)
        
        # Replace history
        self.message_history = summarized
        
        # Reset token tracker (summarized history uses fewer tokens)
        self.token_tracker.reset()
        
        print(f"[Subagent {self.subagent_id}] Summarization complete. New token usage: 0 (reset)")
        print(f"[Subagent {self.subagent_id}] Peak usage before summarization: {self.token_tracker.peak_tokens}")
    
    def _call_model(self, forced_report: bool = False, restrict_tools: bool = False) -> str:
        """Call the model and handle tool calls."""
        try:
            # Get tools definition (potentially restricted)
            tools = self._get_tools_definition(forced_report=forced_report, restrict_tools=restrict_tools)
            
            # Prepare messages
            messages = self._prepare_messages_for_model()
            
            # Call model
            response = self.model_client.chat(
                messages=messages,
                max_completion_tokens=self.max_completion_tokens,
                tools=tools
            )
            
            # Update token tracker
            self.token_tracker.update_usage(response)
            
            # Check if near limit
            if self.token_tracker.is_near_limit():
                print(f"[Subagent {self.subagent_id}] [Summarizing due to token limit]")
                self._summarize_history()
            
            # Get model response
            assistant_message = response["choices"][0]["message"]
            
            # Check for tool calls
            if "tool_calls" in assistant_message and assistant_message["tool_calls"]:
                tool_calls = assistant_message["tool_calls"]
                
                # Add assistant message with tool calls and empty content to history
                assistant_msg = {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": tool_calls
                }
                
                # Add reasoning if available
                reasoning = self.model_client.get_reasoning(response)
                if reasoning:
                    assistant_msg["reasoning_content"] = reasoning
                
                self.message_history.append(assistant_msg)
                
                # Execute tool calls
                self._handle_tool_calls(tool_calls)
                
                return ""  # Return empty as model will continue
            
            # Extract content and reasoning (handle None content)
            content = assistant_message.get("content") or ""
            reasoning = self.model_client.get_reasoning(response)
            
            # Add assistant message to history
            assistant_msg = {
                "role": "assistant",
                "content": content
            }
            if reasoning:
                assistant_msg["reasoning_content"] = reasoning
            
            self.message_history.append(assistant_msg)
            
            return content
            
        except Exception as e:
            print(f"[Subagent {self.subagent_id}] Error calling model: {e}")
            return ""
    
    def _prepare_messages_for_model(self) -> List[Dict[str, Any]]:
        """
        Prepare messages for model API.
        
        Returns:
            List of messages ready for API call
        """
        prepared = []
        
        for msg in self.message_history:
            msg_copy = msg.copy()
            
            # Remove reasoning fields for vLLM compatibility
            if "reasoning_content" in msg_copy:
                msg_copy.pop("reasoning_content")
            if "reasoning" in msg_copy:
                msg_copy.pop("reasoning")
            
            prepared.append(msg_copy)
        
        # Workaround for vLLM add_generation_prompt error
        if prepared and prepared[-1].get("role") == "assistant":
            prepared.append({
                "role": "user",
                "content": "."
            })
        
        return prepared
    
    def _get_tools_definition(self, forced_report: bool = False, restrict_tools: bool = False) -> List[Dict[str, Any]]:
        """Get tool definitions for the subagent.
        
        NOTE: Subagents CANNOT create other subagents. They can only:
        - web_search: Research their assigned subtopic
        - fetch_url: Fetch content from URLs
        - add_findings: Save research notes (can write multiple findings at once)
        - findings_list: List findings
        - findings_read: Read findings
        - generate_report: Create final report (terminating tool)
        
        Dynamic: 
        - After 3 web_search calls, web_search tool is removed entirely.
        - If restrict_tools=True, ONLY generate_report is available.
        """
        tools = []
        
        # If tools are restricted (iteration >= 19), ONLY provide generate_report
        if restrict_tools:
            print(f"[SA {self.subagent_id}] Tools restricted: ONLY generate_report available")
            return [{
                "type": "function",
                "function": {
                    "name": "generate_report",
                    "description": "Generate your final research report. This is a TERMINATING tool - call this when your research is complete. YOU MUST CALL THIS NOW - no other tools are available.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "report_content": {
                                "type": "string",
                                "description": "The complete research report in markdown format"
                            }
                        },
                        "required": ["report_content"]
                    }
                }
            }]
        
        # Check if query limit exhausted (3 web searches max)
        web_query_count = sum(1 for q in self.research_findings.get("search_queries", []) if not q.startswith("URL:"))
        web_search_available = web_query_count < 2
        
        # Add web_search tool if still available
        if web_search_available:
            tools.append({
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "COSTLY: Use sparingly to discover URLs only. Returns titles, snippets, and URLs - NOT full content. After getting URLs, ALWAYS use fetch_url to read actual content. Limited to 3 searches.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query string"
                            },
                            "freshness": {
                                "type": "string",
                                "description": "Time filter: 'pd' (past day), 'pw' (past week), 'pm' (past month), 'py' (past year)",
                                "enum": ["pd", "pw", "pm", "py"]
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
        
        # Always add fetch_url tool
        tools.append({
            "type": "function",
            "function": {
                "name": "fetch_url",
                "description": "Fetch and clean content from a URL. Use this to read web pages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Direct URL to fetch content from"
                        }
                    },
                    "required": ["url"]
                }
            }
        })
        
        # Add findings tools
        tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "add_findings",
                    "description": "Write multiple research findings at once. Each finding can be up to 1000 words. Use this for ALL important information, quotes, statistics, and detailed analysis. Each fact should be a separate finding. Pass an array of {title, content} objects.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "findings": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "Finding title/heading"
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "Finding content (up to 1000 words)"
                                        }
                                    },
                                    "required": ["title", "content"]
                                },
                                "description": "Array of finding objects with title and content"
                            }
                        },
                        "required": ["findings"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "findings_list",
                    "description": "List all findings (ID and title only)",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "findings_read",
                    "description": "Read one or more findings by ID. Can read up to 5 findings at once for context. Use this to review related findings together.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "finding_ids": {
                                "type": ["string", "array"],
                                "description": "Single ID (string) or multiple IDs (array). Example: 'abc123' or ['abc123', 'def456', 'ghi789']"
                            }
                        },
                        "required": ["finding_ids"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_report",
                    "description": "Generate your final research report. This is a TERMINATING tool - call this when your research is complete.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ])
        
        return tools
    
    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> None:
        """
        Handle tool calls from the model - executes up to 3 tools in parallel.
        
        Args:
            tool_calls: List of tool calls from model
        """
        import threading
        from threading import Thread
        
        # Limit to max 3 parallel tool calls
        max_parallel = 3
        tool_batches = []
        
        # Split tool calls into batches of max 3
        for i in range(0, len(tool_calls), max_parallel):
            batch = tool_calls[i:i + max_parallel]
            tool_batches.append(batch)
        
        # Execute each batch in parallel
        for batch_idx, batch in enumerate(tool_batches, 1):
            if len(tool_batches) > 1:
                print(f"[Subagent {self.subagent_id}] [Batch {batch_idx}] Executing {len(batch)} tool(s) in parallel...")
            
            # Thread results storage
            results = []
            threads = []
            
            def execute_tool(tool_call, index):
                """Thread function to execute a tool call."""
                call_id = tool_call.get("id", "")
                function = tool_call.get("function", {})
                tool_name = function.get("name", "")
                
                try:
                    # Parse arguments
                    import json
                    arguments = json.loads(function.get("arguments", "{}"))
                    
                    # Log tool call
                    print(f"[SA {self.subagent_id}] [Tool] {tool_name}")
                    
                    # Validate tool call
                    is_allowed, error_msg = self.tool_validator.validate_tool_call(tool_name)
                    if not is_allowed:
                        print(f"[SA {self.subagent_id}] [Tool Blocked] {error_msg}")
                        results.append((call_id, tool_name, error_msg, None))
                        return  # Exit the function instead of continue
                    
                    # Execute tool
                    result = ""
                    if tool_name == "web_search":
                        query = arguments.get("query", "")
                        freshness = arguments.get("freshness")
                        
                        # Increment counter AFTER successful validation
                        self.tool_validator.increment_web_search()
                        
                        result = self._execute_web_search(query, freshness)
                    elif tool_name == "fetch_url":
                        url = arguments.get("url", "")
                        result = self._execute_fetch_url(url)
                    elif tool_name == "add_findings":
                        result = self._execute_findings_write(arguments)
                    elif tool_name == "findings_list":
                        result = self._execute_findings_list(arguments)
                    elif tool_name == "findings_read":
                        result = self._execute_findings_read(arguments)
                    elif tool_name == "generate_report":
                        result = self._execute_generate_report()
                    else:
                        result = f"Unknown tool: {tool_name}"
                    
                    # Log tool result
                    print(f"[SA {self.subagent_id}] [Result] {tool_name}")
                    
                    results.append((call_id, tool_name, result, None))
                    
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {e}"
                    results.append((call_id, tool_name, "", error_msg))
                    print(f"[Subagent {self.subagent_id}] {error_msg}")
            
            # Create and start threads for this batch
            for i, tool_call in enumerate(batch):
                thread = Thread(target=execute_tool, args=(tool_call, i))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads in this batch to complete
            for thread in threads:
                thread.join()
            
            # Add all results to message history
            for call_id, tool_name, result, error in results:
                if error:
                    result = f"Error: {error}"
                
                self.message_history.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result
                })
    
    def _execute_web_search(self, query: str, freshness: Optional[str] = None) -> str:
        """Execute web_search tool."""
        # Track query
        self.research_findings["search_queries"].append(query)
        web_query_count = sum(1 for q in self.research_findings["search_queries"] if not q.startswith("URL:"))
        print(f"[SA {self.subagent_id}] Query #{web_query_count}: {query[:60]}...")
        
        # Execute web search
        result = self.web_search_tool.web_search(query=query, freshness=freshness)
        
        # Store finding
        self.research_findings["findings"].append({
            "query": query,
            "search_type": "Web search",
            "result": result
        })
        
        return f"Web search results: {result[:500]}..."  # Truncate for context
    
    def _execute_fetch_url(self, url: str) -> str:
        """Execute fetch_url tool."""
        # Track as URL fetch (not counted in web query limit)
        self.research_findings["search_queries"].append(f"URL: {url}")
        
        # Execute URL fetch
        result = self.fetch_url_tool.fetch_url(url)
        
        # Store finding
        self.research_findings["findings"].append({
            "url": url,
            "search_type": "URL fetch",
            "result": result
        })
        
        return result
    
    def _execute_write_file(self, arguments: Dict[str, Any]) -> str:
        """Execute write_file tool. (Deprecated)"""
        return "write_file tool is deprecated. Use add_findings instead."
    
    def _execute_read_file(self, arguments: Dict[str, Any]) -> str:
        """Execute read_file tool. (Deprecated)"""
        return "read_file tool is deprecated. Use findings_read instead."
    
    def _execute_ls(self, arguments: Dict[str, Any]) -> str:
        """Execute ls tool. (Deprecated)"""
        return "ls tool is deprecated. Use findings_list instead."
    
    def _execute_findings_write(self, arguments: Dict[str, Any]) -> str:
        """Execute add_findings tool."""
        findings = arguments.get("findings", [])
        return self.findings_tools.add_findings(findings, self.subagent_id)
    
    def _execute_findings_list(self, arguments: Dict[str, Any]) -> str:
        """Execute findings_list tool."""
        return self.findings_tools.findings_list()
    
    def _execute_findings_read(self, arguments: Dict[str, Any]) -> str:
        """Execute findings_read tool."""
        finding_ids = arguments.get("finding_ids", "")
        return self.findings_tools.findings_read(finding_ids)
    
    def _execute_generate_report(self) -> str:
        """
        Execute generate_report tool - creates final report for this subagent.
        This is a TERMINATING tool.
        
        Returns:
            Concise Q&A report string
        """
        try:
            # Generate concise Q&A style report (not a file)
            report = self._generate_concise_report(error_occurred=None)
            
            # Signal that research is complete
            self.research_complete = True
            
            return report
            
        except Exception as e:
            error_msg = f"Error generating report: {str(e)}"
            print(f"[Subagent {self.subagent_id}] {error_msg}")
            return error_msg
    
    def _is_research_complete(self, response: str) -> bool:
        """
        Check if subagent research is complete.
        
        Args:
            response: Model's response
            
        Returns:
            True if research is complete
        """
        if not response:
            return False
        
        response_lower = response.lower()
        
        # Check for completion signals
        completion_indicators = [
            "research complete",
            "research is complete",
            "done researching",
            "my research is finished",
            "subtopic research complete",
        ]
        
        for indicator in completion_indicators:
            if indicator in response_lower:
                return True
        
        return False
    
    def _summarize_history(self) -> None:
        """
        Summarize message history to free up context space.
        Called when token usage reaches 80% of max context window.
        """
        try:
            print(f"[Subagent {self.subagent_id}] Summarizing message history...")
            
            # Generate summary
            summary = self.summarizer.summarize_history(self.message_history)
            
            # Replace message history with summarized version
            # Keep system message
            system_message = None
            for msg in self.message_history:
                if msg.get("role") == "system":
                    system_message = msg
                    break
            
            # Clear and rebuild
            self.message_history = []
            if system_message:
                self.message_history.append(system_message)
            
            # Add summary as a condensed user message
            self.message_history.append({
                "role": "user",
                "content": f"SUMMARY OF PREVIOUS RESEARCH:\n{summary}"
            })
            
            print(f"[Subagent {self.subagent_id}] Summarization complete. Context freed.")
            
        except Exception as e:
            print(f"[Subagent {self.subagent_id}] Error during summarization: {e}")
    
    def _save_findings(self) -> None:
        """
        Save research findings (deprecated - using centralized findings_db.json).
        Subagents now use add_findings tool to save to shared database.
        """
        pass  # No longer needed - findings are saved via add_findings tool
