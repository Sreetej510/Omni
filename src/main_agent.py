"""Main agent with subagent orchestration for comprehensive research."""
import os
import json
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
from src.utils.state_manager import StateManager
from src.utils.tool_validator import ToolValidator
from src.utils.url_tracker import URLSourceTracker
from src.summarizer_agent import SummarizerAgent
from src.subagent import Subagent
from config.settings import MAX_COMPLETION_TOKENS, MAX_CONTEXT_WINDOW, SUMMARIZATION_THRESHOLD, STATE_STORAGE_PATH, WORKSPACE_ROOT


class MainAgent:
    """
    Main research agent with subagent orchestration:
    - Creates multiple subagents for comprehensive research
    - Manages subagent lifecycle and collects results
    - Real token tracking from API responses
    - Automatic state persistence to JSON
    - Automatic summarization at 80% token capacity
    """
    
    def __init__(
        self,
        model_client: ModelClient,
        web_search_tool: Optional[WebSearchTool] = None,
        fetch_url_tool: Optional[FetchURLTool] = None,
        max_completion_tokens: Optional[int] = None,
        max_context_window: Optional[int] = None
    ):
        """
        Initialize the main research agent with subagent support.
        
        Args:
            model_client: Model client for LLM interactions
            web_search_tool: Web search tool for Brave searches
            fetch_url_tool: URL fetching tool
            max_completion_tokens: Maximum tokens to generate per response
            max_context_window: Maximum total context window size
        """
        self.max_completion_tokens = max_completion_tokens or MAX_COMPLETION_TOKENS
        self.max_context_window = max_context_window or MAX_CONTEXT_WINDOW
        self.model_client = model_client
        
        # Initialize URL source tracker
        self.url_tracker = URLSourceTracker()
        
        # Initialize tools with URL tracker
        self.web_search_tool = web_search_tool or WebSearchTool(
            url_tracker=self.url_tracker
        )
        self.fetch_url_tool = fetch_url_tool or FetchURLTool(
            url_tracker=self.url_tracker
        )
        
        self.token_tracker = TokenTracker(self.max_completion_tokens, self.max_context_window, SUMMARIZATION_THRESHOLD)
        self.state_manager = StateManager(STATE_STORAGE_PATH)
        self.tool_validator = ToolValidator(web_search_limit=5)  # Main agent limit: 5
        self.summarizer = SummarizerAgent(model_client)
        self.report_tool = ReportTool(None)  # Workspace manager not needed
        
        # Subagent management
        self.subagents: List[Subagent] = []
        self.subagent_results: List[Dict[str, Any]] = []
        
        # Iteration tracking for dynamic tool access
        self.current_iteration = 0
        self.subagent_tools_unlocked = False
        
        # Generate unique session ID
        self.session_id = str(uuid.uuid4())[:8]
        
        # Create workspace
        self.workspace = os.path.join(WORKSPACE_ROOT, f"main_agent_{self.session_id}")
        os.makedirs(self.workspace, exist_ok=True)
        
        # Initialize file system tool AFTER workspace is created
        self.file_system_tool = FileSystemTool(self.workspace)
        
        # Initialize findings manager and tools (shared across all agents for this topic)
        self.findings_manager = FindingsManager(self.workspace)
        self.findings_tools = FindingsTools(self.findings_manager)
        
        self.message_history: List[Dict[str, str]] = []
        self.current_topic = ""
        self.research_complete = False
        # Multi-section report state
        self.report_sections: List[Dict[str, Any]] = []
        self.in_report_mode = False
        self.research_data: Dict[str, Any] = {
            "topic": "",
            "subtopics": [],
            "search_queries": [],
            "findings": [],
            "subagent_results": [],
            "final_report": None
        }
        
        # Initialize with system message
        self.message_history.append({
            "role": "system",
            "content": self._get_system_prompt()
        })
        
        print(f"Initialized research agent session: {self.session_id}")
        print(f"Max completion tokens: {self.max_completion_tokens}")
        print(f"Max context window: {self.max_context_window}")
        print(f"Summarization threshold: {SUMMARIZATION_THRESHOLD * 100}%")
        print(f"Workspace: {self.workspace}")
    
    def _get_system_prompt(self) -> str:
        """Get unified system prompt for the main agent."""
        return """You are a research coordinator. Research: {topic}

CRITICAL: You do NOT do web_search or fetch_url yourself. Subagents handle ALL web research.

YOUR ROLE:
- Create subagents to research subtopics
- Read findings from subagents
- Synthesize findings into comprehensive report

AVAILABLE TOOLS:
- create_subagent: Delegate research to subagents (use this extensively!)
- add_findings: Save important observations (can write multiple at once)
- findings_list: List all findings (ID and title only)
- findings_read: Read one or more findings by ID
- report_add_section: Add sections to final report (levels 1-3 only)
- report_finalize: Finalize and save report (requires title)

WORKFLOW:
1. Analyze the topic and identify 3-5 distinct subtopics
2. Create subagents for each subtopic with VERY SPECIFIC instructions
3. Subagents will research in parallel (they will web_search, fetch_url, add_findings)
4. Read all findings with findings_list/findings_read
5. Synthesize findings into comprehensive multi-section report
6. Call report_finalize with a short title when complete

REPORT FORMAT:
- 5-7 main sections maximum
- Use levels 1-3 ONLY (1=title, 2=main section, 3=subsection)
- Prefer paragraphs over bullets
- If using bullets: 3-5 max per subsection, 1-2 substantive sentences each
- Focus on SYNTHESIS, not listing every detail
- ALL content MUST be from research findings - NO speculations

CRITICAL RULES:
- Do NOT attempt web_search or fetch_url - subagents do this
- Create MULTIPLE subagents (3-5) for comprehensive coverage
- Each subagent needs specific, detailed task description
- Subagents handle all web research, PDF fetching, and findings
- Your value is in coordination, synthesis, and report writing
- Read findings BEFORE writing report to understand what was discovered

Call tools - do not just describe them!"""
    
    def _get_tools_definition(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions for the model - simplified for subagent coordination only.
        
        Available tools:
        - create_subagent: Available from iteration 1
        - add_findings, findings_list, findings_read: Available always
        - report_add_section, report_finalize: Available always
        - web_search, fetch_url: REMOVED (subagents handle this)
        
        Returns:
            List of tool definitions in OpenAI tool format
        """
        tools = []
        
        # Add subagent tools - available from iteration 1
        tools.append({
            "type": "function",
            "function": {
                "name": "create_subagent",
                "description": "Create a subagent to research a specific subtopic. Use this to delegate ALL web research. Subagents will handle web_search, fetch_url, and add_findings. Main agent only coordinates and synthesizes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The specific subtopic name for the subagent"
                        },
                        "task": {
                            "type": "string",
                            "description": "Detailed instructions for what the subagent should research. Be very specific with focus areas, search targets, and expected outputs."
                        }
                    },
                    "required": ["name", "task"]
                }
            }
        })
        
        # Add findings and report tools
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
                    "name": "report_add_section",
                    "description": "Add a section to the final report. Build a focused report with 5-7 main sections. Each section must be meaningful and relevant ONLY from research - no speculations. HEADING LEVELS: Use 1-3 ONLY (1=title, 2=main sections, 3=subsections). NO level 4+. FORMAT: Prefer paragraphs over bullets. If using bullets, limit to 3-5 per subsection, each bullet 1-2 substantive sentences. Avoid redundant headings. Focus on SYNTHESIS not listing every detail. NOT terminating - continue until report is complete, then call report_finalize.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Section heading text - concise and descriptive"
                            },
                            "level": {
                                "type": "integer",
                                "description": "Heading level 1-3 ONLY (1=title, 2=main section, 3=subsection)",
                                "minimum": 1,
                                "maximum": 3
                            },
                            "content": {
                                "type": "string",
                                "description": "Section content from research only - no speculations. Prefer paragraphs. If using bullets: 3-5 max, 1-2 substantive sentences each. Avoid excessive detail - focus on synthesis."
                            }
                        },
                        "required": ["title", "level", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "report_finalize",
                    "description": "TERMINATING: Finalize and save the complete report. Call this ONLY AFTER all sections have been added via report_add_section. Requires a short title for the report file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Short title for the report (used as filename)"}
                        },
                        "required": ["title"]
                    }
                }
            }
        ])
        
        return tools
    
    def _prepare_messages_for_model(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare messages for sending to model.
        Removes reasoning fields and ensures last message is from user for vLLM compatibility.
        This creates a copy only when needed for API calls.
        
        Args:
            messages: Original message history
            
        Returns:
            New list with reasoning fields removed and proper message structure for vLLM
        """
        prepared = []
        for msg in messages:
            # Create a copy of the message
            msg_copy = msg.copy()
            
            # Remove reasoning fields for vLLM compatibility
            # vLLM doesn't support reasoning_content or reasoning fields
            msg_copy.pop("reasoning_content", None)
            msg_copy.pop("reasoning", None)
            
            prepared.append(msg_copy)
        
        # vLLM workaround: if last message is from assistant, add a dummy user message
        # This prevents the "add_generation_prompt" error
        if prepared and prepared[-1].get("role") == "assistant":
            prepared.append({
                "role": "user",
                "content": ""
            })
        
        return prepared
    
    def _execute_create_subagent(self, subtopic: str, instructions: str) -> str:
        """
        Execute create_subagent tool - creates AND runs the subagent.
        Subagent will research its subtopic and return a report.
        
        Args:
            subtopic: Subtopic to research
            instructions: Research instructions
            
        Returns:
            Subagent's final report
        """
        try:
            print(f"\n{'='*70}")
            print(f"CREATING SUBAGENT for: {subtopic}")
            print(f"{'='*70}")
            
            # Create subagent
            subagent = Subagent(
                subtopic=subtopic,
                instructions=instructions,
                parent_workspace=self.workspace,
                model_client=self.model_client,
                web_search_tool=self.web_search_tool,
                fetch_url_tool=self.fetch_url_tool,
                max_completion_tokens=self.max_completion_tokens,
                max_context_window=self.max_context_window
            )
            
            # Add to list
            self.subagents.append(subagent)
            self.research_data["subtopics"].append(subtopic)
            
            print(f"\nSubagent {subagent.subagent_id} created for: {subtopic}")
            print(f"Starting research...")
            print(f"{'='*70}\n")
            
            # RUN THE SUBAGENT - this will block until research is complete
            report = subagent.research()
            
            print(f"\nSubagent {subagent.subagent_id} completed research on: {subtopic}")
            print(f"{'='*70}\n")
            
            return report
            
        except Exception as e:
            error_msg = f"Error creating subagent: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg
    
    def run_all_subagents_parallel(self) -> None:
        """
        Run all created subagents in parallel.
        Called after model creates multiple subagents.
        """
        if not self.subagents:
            print("\nNo subagents to run.")
            return
        
        print(f"\n{'='*70}")
        print(f"RUNNING {len(self.subagents)} SUBAGENT(S) IN PARALLEL")
        print(f"{'='*70}\n")
        
        # Import threading for parallel execution
        import threading
        from threading import Thread
        
        # Thread results storage
        results = []
        threads = []
        
        def run_subagent(subagent, index):
            """Thread function to run a subagent."""
            try:
                print(f"\n[Thread {index}] Starting subagent {subagent.subagent_id}")
                # subagent.research() now returns a report string, not a dict
                report = subagent.research()
                results.append((index, report, None))
                print(f"[Thread {index}] Subagent {subagent.subagent_id} completed")
            except Exception as e:
                results.append((index, None, e))
                print(f"[Thread {index}] Subagent error: {e}")
        
        # Create and start threads for all subagents
        for i, subagent in enumerate(self.subagents, 1):
            thread = Thread(target=run_subagent, args=(subagent, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results - now subagents return report strings, not dicts
        for index, report, error in results:
            if error:
                print(f"[WARNING] Subagent {index} failed: {error}")
                # Store error message as report
                self.subagent_results.append(f"[ERROR from Subagent {index}]: {error}")
            else:
                # report is now a string (the full report content)
                self.subagent_results.append(report)
        
        print(f"\n[{len(self.subagents)} subagents completed]")
    
    def _execute_consolidate_results(self) -> str:
        """
        Execute consolidate_subagent_results tool.
        First runs any pending subagents in parallel, then consolidates results.
        
        Returns:
            Consolidated findings from all subagents
        """
        # First, run any pending subagents in parallel
        if self.subagents and not self.subagent_results:
            print(f"[Running {len(self.subagents)} subagents]")
            self.run_all_subagents_parallel()
        
        if not self.subagent_results:
            return "No subagent results to consolidate yet."
        
        consolidated = []
        
        for i, report in enumerate(self.subagent_results, 1):
            # report is now a string (full report content)
            if report.startswith("[ERROR"):
                consolidated.append(f"=== SUBAGENT {i}: ERROR ===")
                consolidated.append(report)
            else:
                # Extract first few lines as summary
                lines = report.split("\n")
                title_line = lines[0] if lines else f"Subagent {i}"
                consolidated.append(f"=== SUBAGENT {i}: {title_line} ===")
                consolidated.append(f"Report length: {len(report)} characters")
                consolidated.append("")
                consolidated.append("Report content:")
                consolidated.append(report[:1000] + "..." if len(report) > 1000 else report)
            
            consolidated.append("")
        
        # Save consolidated results
        consolidated_text = "\n".join(consolidated)
        consolidated_path = os.path.join(self.workspace, "consolidated_results.txt")
        
        with open(consolidated_path, 'w', encoding='utf-8') as f:
            f.write(consolidated_text)
        
        return f"Consolidated results from {len(self.subagent_results)} subagent(s). Saved to: {consolidated_path}"
    
    def _execute_web_search(self, query: str, freshness: Optional[str] = None) -> str:
        """
        Execute the web_search tool.
        
        Args:
            query: Search query
            freshness: Time filter
            
        Returns:
            Search results as formatted string
        """
        try:
            results = self.web_search_tool.web_search(
                query=query,
                freshness=freshness
            )
            return results
        except Exception as e:
            return f"Web search error: {str(e)}"
    
    def _execute_fetch_url(self, url) -> str:
        """
        Execute the fetch_url tool.
        
        Args:
            url: Single URL (string) or multiple URLs (array)
            
        Returns:
            Fetched and cleaned content
        """
        try:
            # Handle both single URL and batch mode
            if isinstance(url, str):
                # Single URL
                result = self.fetch_url_tool.fetch_url(url)
                return result
            elif isinstance(url, list):
                # Batch mode - fetch multiple URLs in parallel
                result = self.fetch_url_tool.fetch_urls_batch(url, max_urls=5)
                return result
            else:
                return "Error: url must be a string or array of strings"
        except Exception as e:
            return f"Error executing fetch_url: {str(e)}"
            return f"URL fetch error: {str(e)}"
    
    def _execute_write_file(self, filepath: str, content: str) -> str:
        """
        Execute write_file tool. (Deprecated - kept for compatibility)
        """
        return "write_file tool is deprecated. Use findings_write instead."
    
    def _execute_read_file(self, filepath: str) -> str:
        """
        Execute read_file tool. (Deprecated - kept for compatibility)
        """
        return "read_file tool is deprecated. Use findings_read instead."
    
    def _execute_ls(self, arguments: Dict[str, Any]) -> str:
        """
        Execute ls tool. (Deprecated - kept for compatibility)
        """
        return "ls tool is deprecated. Use findings_list instead."
    
    def _execute_findings_write(self, arguments: Dict[str, Any]) -> str:
        """Execute add_findings tool."""
        findings = arguments.get("findings", [])
        return self.findings_tools.add_findings(findings, self.session_id)
    
    def _execute_findings_list(self, arguments: Dict[str, Any]) -> str:
        """Execute findings_list tool."""
        return self.findings_tools.findings_list()
    
    def _execute_findings_read(self, arguments: Dict[str, Any]) -> str:
        """Execute findings_read tool."""
        finding_ids = arguments.get("finding_ids", "")
        return self.findings_tools.findings_read(finding_ids)
    
    def _execute_ls(self, arguments: Dict[str, Any]) -> str:
        """
        Execute ls tool. (Deprecated - kept for compatibility)
        
        Args:
            arguments: Tool arguments with optional directory
            
        Returns:
            Directory listing or error
        """
        directory = arguments.get("directory", ".")
        
        # Handle relative paths
        if directory == "." or directory == "":
            directory = self.workspace
        elif not directory.startswith(self.workspace):
            directory = os.path.join(self.workspace, directory)
        
        return "ls tool is deprecated. Use findings_list instead."
    
    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> None:
        """
        Handle tool calls from the model.
        - Non-subagent tools: execute sequentially
        - Subagent tools: execute in parallel and wait for all to complete
        
        Note: Tool calls should already be limited to max 3 before calling this method.
        
        Args:
            tool_calls: List of tool call dictionaries (max 3)
        """
        import threading
        from threading import Thread
        
        # Separate subagent calls from other tools
        subagent_calls = []
        other_calls = []
        
        for tool_call in tool_calls:
            function_name = tool_call.get("function", {}).get("name", "")
            if function_name == "create_subagent":
                subagent_calls.append(tool_call)
            else:
                other_calls.append(tool_call)
        
        # Execute non-subagent tools sequentially
        for tool_call in other_calls:
            self._execute_single_tool(tool_call)
        
        # Execute subagents in parallel and wait for all
        if subagent_calls:
            print(f"[Executing {len(subagent_calls)} subagent(s) in parallel]")
            self._execute_subagents_parallel(subagent_calls)
    
    def _execute_single_tool(self, tool_call: Dict[str, Any]) -> None:
        """
        Execute a single non-subagent tool and add result to history.
        
        Args:
            tool_call: Tool call dictionary
        """
        function_name = tool_call.get("function", {}).get("name", "")
        arguments = tool_call.get("function", {}).get("arguments", "{}")
        
        # Parse arguments
        try:
            import json
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
        except:
            args = {}
        
        # Log tool call
        print(f"[Tool] {function_name}")
        
        # Validate tool call
        is_allowed, error_msg = self.tool_validator.validate_tool_call(function_name)
        if not is_allowed:
            print(f"[Tool Blocked] {error_msg}")
            self.message_history.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": error_msg
            })
            return
        
        # Execute the appropriate tool
        result = ""
        try:
            if function_name == "add_findings":
                findings = args.get("findings", [])
                result = self._execute_findings_write({"findings": findings})
            elif function_name == "findings_list":
                result = self._execute_findings_list({})
            elif function_name == "findings_read":
                finding_ids = args.get("finding_ids", "")
                result = self._execute_findings_read({"finding_ids": finding_ids})
            elif function_name == "report_add_section":
                title = args.get("title", "")
                level = max(1, min(3, args.get("level", 2)))  # Limit to level 3 max
                content = args.get("content", "")
                self.report_sections.append({"title": title, "level": level, "content": content})
                self.in_report_mode = True
                n = len(self.report_sections)
                level_desc = {1: "Title", 2: "Main Section", 3: "Subsection"}
                result = f"Section #{n} added: '{title}' (level {level} - {level_desc.get(level, 'Unknown')}, {len(content)} chars). Continue with report_add_section or call report_finalize when complete."
            elif function_name == "report_finalize":
                title = args.get("title", "")
                if not title:
                    result = "Error: report_finalize requires a 'title' parameter. Provide a short title for the report file."
                elif not self.report_sections:
                    result = "Error: No sections added yet. Call report_add_section first to build the report."
                else:
                    path = self._save_multi_section_report(title)
                    self.research_complete = True
                    result = f"Report finalized: {len(self.report_sections)} sections saved to {path}"
            else:
                result = f"Unknown function: {function_name}"
            
            # Log tool result
            result_preview = result[:200] + "..." if len(result) > 200 else result
            print(f"[Tool Result] {function_name} completed")
            print(f"  Result: {result_preview}")
            print("=" * 60)
            
            # Add result to message history
            self.message_history.append({
                "role": "tool",
                "content": result,
                "name": function_name,
                "tool_call_id": tool_call.get("id", "")
            })
            
        except Exception as e:
            error_msg = f"Error executing {function_name}: {str(e)}"
            print(f"[Tool Error] {error_msg}")
            self.message_history.append({
                "role": "tool",
                "content": f"Error: {error_msg}",
                "name": function_name,
                "tool_call_id": tool_call.get("id", "")
            })
    
    def _execute_subagents_parallel(self, subagent_calls: List[Dict[str, Any]]) -> None:
        """
        Execute multiple subagents in parallel and wait for all to complete.
        
        Args:
            subagent_calls: List of create_subagent tool calls
        """
        import threading
        from threading import Thread
        
        results = []
        threads = []
        
        def create_and_run_subagent(tool_call, index):
            """Thread function to create and run a subagent."""
            arguments = tool_call.get("function", {}).get("arguments", "{}")
            
            # Parse arguments
            try:
                import json
                if isinstance(arguments, str):
                    args = json.loads(arguments)
                elif isinstance(arguments, dict):
                    args = arguments
                else:
                    args = {}
                
                # Debug: print raw arguments
                print(f"[DEBUG] Raw arguments type: {type(arguments)}")
                print(f"[DEBUG] Parsed args: {args}")
            except Exception as parse_error:
                print(f"[ERROR] Failed to parse arguments: {str(parse_error)}")
                print(f"[ERROR] Arguments value: {arguments}")
                args = {}
            
            # Extract subtopic and instructions (using correct parameter names)
            subtopic = args.get("name", "")
            instructions = args.get("task", "")
            
            # Validate required fields
            if not subtopic or not instructions:
                print(f"[ERROR] Missing required fields!")
                print(f"[ERROR] name: '{subtopic}'")
                print(f"[ERROR] task: '{instructions}'")
            
            try:
                print(f"[Subagent {index}] Creating subagent for: {subtopic}")
                # Create and run subagent (this will block until subagent completes)
                result = self._execute_create_subagent(subtopic, instructions)
                results.append((tool_call.get("id", ""), result, None))
                print(f"[Subagent {index}] Completed: {subtopic}")
            except Exception as e:
                error_msg = f"Error in subagent {subtopic}: {str(e)}"
                results.append((tool_call.get("id", ""), "", error_msg))
                print(f"[Subagent {index}] Error: {error_msg}")
        
        # Create and start threads for all subagents
        for i, tool_call in enumerate(subagent_calls, 1):
            thread = Thread(target=create_and_run_subagent, args=(tool_call, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all subagent threads to complete
        for thread in threads:
            thread.join()
        
        # Add all subagent results to message history
        print(f"\n[Subagents] All {len(subagent_calls)} subagent(s) completed")
        for call_id, result, error in results:
            if error:
                result = f"Error: {error}"
            
            self.message_history.append({
                "role": "tool",
                "content": result,
                "name": "create_subagent",
                "tool_call_id": call_id
            })
    
    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        """
        Call the model and track token usage.
        Handles tool calls automatically.
        
        Args:
            messages: Message history to send
            
        Returns:
            Model response content or empty string if tool calls were made
        """
        # Prepare messages for model
        prepared_messages = self._prepare_messages_for_model(messages)
        
        # Get tool definitions
        tools = self._get_tools_definition()
        
        # Call model with max completion tokens and tools
        response = self.model_client.chat(
            messages=prepared_messages, 
            tools=tools,
            max_completion_tokens=self.max_completion_tokens
        )
        
        # Track token usage from response
        self.token_tracker.update_usage(response)
        
        # Check if near limit
        if self.token_tracker.is_near_limit():
            print("[Summarizing due to token limit]")
            self._summarize_history()
        
        # Check for tool calls
        tool_calls = self.model_client.get_tool_calls(response)
        
        if tool_calls:
            print(f"\nModel is calling {len(tool_calls)} tool(s)...")
            
            # Add assistant message with tool calls to history (only the limited ones)
            assistant_message = {
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls
            }
            
            # Add reasoning if available
            reasoning = self.model_client.get_reasoning(response)
            if reasoning:
                assistant_message["reasoning_content"] = reasoning
            
            self.message_history.append(assistant_message)
            
            # Execute the tool calls
            self._handle_tool_calls(tool_calls)
            
            print("Tool calls executed.")
            return ""  # Return empty since we executed tools
        else:
            # No tool calls, just content
            content = self.model_client.get_content(response) or ""
            
            # Add assistant message to history
            assistant_message = {
                "role": "assistant",
                "content": content
            }
            
            # Add reasoning if available
            reasoning = self.model_client.get_reasoning(response)
            if reasoning:
                assistant_message["reasoning_content"] = reasoning
            
            self.message_history.append(assistant_message)
            
            return content
    
    def _summarize_history(self):
        """Summarize message history when approaching token limit."""
        print(f"Current token usage: {self.token_tracker.context_tokens}")
        print(f"Summarizing to free up context...")
        
        # Save state before summarization
        self.save_state(status="summarizing")
        
        # Create summarized history
        summarized = self.summarizer.create_summarized_history(self.message_history)
        
        # Replace history
        self.message_history = summarized
        
        # Reset token tracker (summarized history uses fewer tokens)
        self.token_tracker.reset()
        
        # Save summarized state
        self.save_state(is_summarized=True, status="active")
        
        print(f"Summarization complete. New token usage: 0 (reset)")
        print(f"Peak usage before summarization: {self.token_tracker.peak_tokens}")
    
    def research(self, topic: str) -> str:
        """
        Execute research on a topic.
        
        Args:
            topic: Research topic
            
        Returns:
            Final research report
        """
        print(f"\n[Starting research: {topic}]")
        
        # Update state
        self.current_topic = topic
        self.research_data["topic"] = topic
        
        # Add topic to conversation
        self.message_history.append({
            "role": "user",
            "content": f"Research this topic comprehensively: {topic}"
        })
        
        # Save initial state
        self.save_state(status="active")
        
        # Initialize iteration counter
        self.current_iteration = 0
        
        # Hard iteration cap for safety
        max_iterations = 50
        
        # Research loop
        while True:
            self.current_iteration += 1
            context_pct = (self.model_client.get_current_prompt_tokens() / self.max_context_window) * 100
            
            # Display iteration status
            print(f"\n[Iteration {self.current_iteration}/{max_iterations}] Context: {self.model_client.get_current_prompt_tokens()}/{self.max_context_window} ({context_pct:.1f}%)")
            
            # Check if near context limit BEFORE calling model
            context_pct = (self.model_client.get_current_prompt_tokens() / self.max_context_window) * 100
            print(f"[Context Check] Tokens: {self.model_client.get_current_prompt_tokens()}/{self.max_context_window} ({context_pct:.1f}%)")
            
            if context_pct >= 80:
                print(f"[Pre-emptive summarization due to context limit at {context_pct:.1f}%]")
                self._summarize_history()
            elif context_pct > 90:
                print(f"[CRITICAL] Context at {context_pct:.1f}% - forcing summarization!")
                self._summarize_history()
            
            # Call model to decide next action
            response = self._call_model(self.message_history)
            # Encode to handle Unicode characters
            response_preview = response[:200]
            try:
                print(f"Response: {response_preview}...")
            except UnicodeEncodeError:
                # Fallback: print encoded version
                safe_preview = response_preview.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                print(f"Response: {safe_preview}...")
            
            # Check if research is complete
            if self._is_research_complete(response) or self.research_complete:
                print("Research complete. Report finalized.")
                break
            
            # Hard cap on total iterations
            if self.current_iteration >= max_iterations:
                print(f"[Hard iteration cap ({max_iterations}) reached - forcing exit]")
                # If we have sections but no finalize was called, save what we have
                if self.report_sections and not self.research_complete:
                    print(f"[Auto-finalizing with {len(self.report_sections)} sections]")
                    self._save_multi_section_report()
                    self.research_complete = True
                break
            
            # Save state after each iteration
            self.save_state(status="active")
        
        # Save final state (report already saved by generate_final_report tool)
        self.save_state(
            research_data=self.research_data,
            status="completed"
        )
        
        report = self.research_data.get("final_report", "Report not generated")
        
        usage_info = self.token_tracker.get_usage_info()
        print("\n[Research Complete]")
        print(f"Completion tokens: {usage_info['completion_tokens']}")
        print(f"Context: {usage_info['context_tokens']}/{usage_info['max_context_window']}")
        print(f"Peak: {usage_info['peak_context_tokens']}")
        
        return report
    
    def _is_research_complete(self, last_response: str) -> bool:
        """
        Check if research is complete based on model response.
        
        Args:
            last_response: Last model response
            
        Returns:
            True if research appears complete
        """
        # Check for explicit completion signals (not just planning words)
        complete_indicators = [
            "generate final report",
            "create final report",
            "write final report",
            "produce final report",
            "compile final report",
            "research is complete",
            "research complete.",
            "done researching",
            "finished researching",
            "conclude research"
        ]
        
        response_lower = last_response.lower()
        
        # Must have explicit completion signal
        return any(indicator in response_lower for indicator in complete_indicators)
    
    def _save_multi_section_report(self, title: str) -> str:
        """Save multi-section report assembled from accumulated sections only (no findings)."""
        # Build report body from accumulated sections (preserves model-defined hierarchy)
        report_body = ""
        for section in self.report_sections:
            heading_marker = "#" * section["level"]
            report_body += f"\n\n{heading_marker} {section['title']}\n\n{section['content']}"
        
        # Assemble complete markdown document (no findings appendix)
        final_output = f"# {title}\n\n"
        final_output += f"**Generated:** {self._get_timestamp()}\n\n"
        final_output += "=" * 80
        final_output += report_body
        
        # Save to reports folder with title-based filename
        os.makedirs("reports", exist_ok=True)
        safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in title).strip()
        report_filename = f"{safe_title.lower().replace(' ', '_')}.md"
        report_file = os.path.join("reports", report_filename)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(final_output)
        
        print(f"\n[Multi-Section Report Saved]")
        print(f"  File: {report_file}")
        print(f"  Sections: {len(self.report_sections)}")
        print(f"  Total size: {len(final_output)} characters")
        
        # Store in research data
        self.research_data["final_report"] = final_output
        
        return report_file
    
    def _save_final_report(self, report_content: str) -> str:
        """Save final report combining model's report with findings database."""
        # Read all findings from database
        all_findings = self.findings_manager.list_findings()
        findings_text = []
        
        for finding in all_findings:
            full_data = self.findings_manager.read_finding(finding['id'])
            if full_data:
                findings_text.append(f"### {finding['title']}\n{full_data['content']}")
        
        # Create comprehensive markdown file
        final_output = f"# Research Report: {self.current_topic}\n\n"
        final_output += f"**Session ID:** {self.session_id}\n"
        final_output += f"**Generated:** {self._get_timestamp()}\n"
        final_output += f"**Total Findings:** {len(all_findings)}\n\n"
        final_output += "=" * 80 + "\n\n"
        
        # Add model's report
        final_output += "## Detailed Report\n\n"
        final_output += report_content
        final_output += "\n\n"
        final_output += "=" * 80 + "\n\n"
        
        # Add findings database
        final_output += "## Supporting Findings\n\n"
        if findings_text:
            final_output += "\n\n---\n\n".join(findings_text)
        else:
            final_output += "No supporting findings.\n"
        
        # Save to file
        report_file = os.path.join(self.workspace, "final_report.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(final_output)
        
        print(f"Final report saved to: {report_file}")
        print(f"Total size: {len(final_output)} characters")
        
        # Store in research data
        self.research_data["final_report"] = final_output
        
        return report_file
    
    def save_state(self, **kwargs):
        """
        Save current agent state to JSON file.
        
        Args:
            **kwargs: Additional state updates
        """
        self.state_manager.save_state(
            session_id=self.session_id,
            message_history=self.message_history,
            research_data=self.research_data,
            status=kwargs.get("status", "active"),
            is_summarized=kwargs.get("is_summarized", False),
            total_tokens_used=self.token_tracker.context_tokens,
            topic=self.current_topic
        )
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @classmethod
    def load_from_session(cls, session_id: str, model_client: ModelClient, web_search_tool: WebSearchTool, fetch_url_tool: FetchURLTool):
        """
        Load agent state from a saved session.
        
        Args:
            session_id: Session ID to load
            model_client: Model client for LLM interactions
            web_search_tool: Web search tool for Brave searches
            fetch_url_tool: URL fetching tool
            
        Returns:
            MainAgent instance with loaded state
        """
        # Create new instance
        agent = cls(model_client=model_client, web_search_tool=web_search_tool, fetch_url_tool=fetch_url_tool)
        
        # Load state
        state = agent.state_manager.load_state(session_id)
        if state:
            agent.session_id = session_id
            agent.message_history = state.get("agent_state", {}).get("message_history", [])
            agent.research_data = state.get("research_data", {})
            agent.current_topic = agent.research_data.get("topic", "")
            
            print(f"Loaded session: {session_id}")
            print(f"Topic: {agent.current_topic}")
            print(f"Status: {state.get('status')}")
        else:
            raise ValueError(f"Session not found: {session_id}")
        
        return agent
