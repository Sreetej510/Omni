#!/usr/bin/env python3
"""
Simplified Multi-Agent Research System - Main Entry Point

Usage:
    python main.py "Your research topic here"
"""
import sys
# Set stdout to UTF-8 to handle Unicode characters
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from src.api.model_client import ModelClient
from src.tools.web_search_tool import WebSearchTool
from src.tools.fetch_url_tool import FetchURLTool
from src.main_agent import MainAgent
from config.settings import MAX_COMPLETION_TOKENS, MAX_CONTEXT_WINDOW


def main():
    """Main entry point - only accepts a research topic."""
    # Get topic from command line arguments
    if len(sys.argv) < 2:
        print("Usage: python main.py \"Your research topic here\"")
        print("\nNo topic provided. Please provide a research topic.")
        sys.exit(1)
    
    topic = " ".join(sys.argv[1:])
    
    print("\nInitializing research system...")
    
    # Initialize components with default token limits
    model_client = ModelClient(
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        max_context_window=MAX_CONTEXT_WINDOW
    )
    web_search_tool = WebSearchTool()
    fetch_url_tool = FetchURLTool()
    
    # Create main agent
    agent = MainAgent(
        model_client=model_client,
        web_search_tool=web_search_tool,
        fetch_url_tool=fetch_url_tool,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        max_context_window=MAX_CONTEXT_WINDOW
    )
    
    # Run research
    print(f"\nResearching topic: {topic}")
    print("=" * 60)
    report = agent.research(topic)
    
    return report


if __name__ == "__main__":
    main()
