"""
Main entry point for BrowserBot application.
"""

import asyncio
import sys
from typing import Optional
import argparse

from .agents.browser_agent import BrowserAgent
from .core.config import settings
from .core.logger import get_logger

logger = get_logger(__name__)


async def interactive_mode():
    """Run BrowserBot in interactive mode."""
    print("🤖 BrowserBot Interactive Mode")
    print("Type 'help' for commands, 'quit' to exit")
    print("-" * 50)
    
    async with BrowserAgent() as agent:
        while True:
            try:
                user_input = input("\nBrowserBot> ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                    
                elif user_input.lower() == 'help':
                    print_help()
                    continue
                    
                elif user_input.lower() == 'status':
                    stats = agent.get_session_stats()
                    print(f"Session ID: {stats['session_id']}")
                    print(f"Model: {stats['model_name']}")
                    print(f"Conversation length: {stats['conversation_length']}")
                    print(f"Active browsers: {stats['browser_stats']['active_browsers']}")
                    continue
                    
                elif user_input.lower() == 'screenshot':
                    print("Taking screenshot...")
                    screenshot = await agent.take_screenshot(full_page=True)
                    if screenshot:
                        filename = f"screenshot_{agent.session_id}.png"
                        with open(filename, 'wb') as f:
                            f.write(screenshot)
                        print(f"Screenshot saved as {filename}")
                    else:
                        print("No active page to screenshot")
                    continue
                    
                elif user_input.lower() == 'clear':
                    agent.clear_conversation_history()
                    print("Conversation history cleared")
                    continue
                
                # Process as task or chat
                print("🤔 Processing...")
                
                if user_input.startswith("task:"):
                    # Execute as task
                    task = user_input[5:].strip()
                    result = await agent.execute_task(task)
                    
                    if result["success"]:
                        print("✅ Task completed successfully!")
                        print(f"Result: {result['output']}")
                    else:
                        print("❌ Task failed:")
                        print(f"Error: {result['error']}")
                        
                else:
                    # Process as chat
                    response = await agent.chat(user_input)
                    
                    if response["success"]:
                        print(f"🤖 {response['response']}")
                    else:
                        print(f"❌ Error: {response['error']}")
                        
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit properly")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                logger.error("Interactive mode error", error=str(e))


def print_help():
    """Print help information."""
    help_text = """
🤖 BrowserBot Commands:

Basic Commands:
  help          - Show this help message
  status        - Show session status
  screenshot    - Take a screenshot of current page
  clear         - Clear conversation history
  quit/exit/q   - Exit BrowserBot

Usage:
  • Just type naturally to chat with the agent
  • Prefix with 'task:' for structured task execution
  • The agent can navigate websites, click elements, extract data, and more

Examples:
  Go to google.com and search for "python web scraping"
  task: Find the latest news on CNN and summarize the headlines
  Navigate to Amazon and find the best-selling books
  Take a screenshot of the current page

The agent will use browser automation tools to complete your requests!
    """
    print(help_text)


async def execute_single_task(task: str):
    """Execute a single task and exit."""
    print(f"🤖 Executing task: {task}")
    print("-" * 50)
    
    async with BrowserAgent() as agent:
        result = await agent.execute_task(task)
        
        if result["success"]:
            print("✅ Task completed successfully!")
            print(f"Result: {result['output']}")
            
            # Print action history
            if result.get('action_history'):
                print("\n📋 Actions taken:")
                for i, action in enumerate(result['action_history'], 1):
                    print(f"  {i}. {action.action}: {action.element or 'page'}")
                    
        else:
            print("❌ Task failed:")
            print(f"Error: {result['error']}")
            sys.exit(1)


async def stream_task(task: str):
    """Execute a task with streaming output."""
    print(f"🤖 Streaming task: {task}")
    print("-" * 50)
    
    async with BrowserAgent() as agent:
        async for update in agent.stream_task(task):
            if update["type"] == "start":
                print(f"🚀 Starting task: {update['task']}")
            elif update["type"] == "status":
                print(f"ℹ️  {update['message']}")
            elif update["type"] == "step":
                print(f"🔄 Step {update['step']}: {update['action']}")
            elif update["type"] == "result":
                print(f"✅ Result: {update['output']}")
            elif update["type"] == "error":
                print(f"❌ Error: {update['error']}")
                sys.exit(1)
            elif update["type"] == "complete":
                print("🎉 Task completed!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="BrowserBot - AI-powered browser automation")
    parser.add_argument(
        "--task", 
        type=str, 
        help="Execute a single task and exit"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream task execution with real-time updates"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Configure settings based on arguments
    if args.headless:
        settings.browser_headless = True
        
    if args.debug:
        settings.log_level = "DEBUG"
    
    try:
        if args.task:
            if args.stream:
                asyncio.run(stream_task(args.task))
            else:
                asyncio.run(execute_single_task(args.task))
        else:
            asyncio.run(interactive_mode())
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error("Application error", error=str(e))
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()