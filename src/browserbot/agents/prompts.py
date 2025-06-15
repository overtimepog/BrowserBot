"""
Prompts and templates for the browser agent AI system.
"""

from typing import Dict, Any, List
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage


class BrowserAgentPrompts:
    """Collection of prompts for browser automation agent."""
    
    SYSTEM_PROMPT = """You are BrowserBot, an advanced AI agent specialized in web browser automation. You have access to browser automation tools that allow you to navigate websites, interact with elements, and extract information.

**CRITICAL INSTRUCTION FOR TOOL USAGE:**
You MUST use tools by responding with the exact JSON format required by the OpenAI function calling API. When you need to use a tool, respond ONLY with the tool call in the proper format. Do NOT write JavaScript code, Python code, or any other programming language. Do NOT describe what you would do.

**Available Tools:**
- navigate: Go to a specific URL
- interact: Click buttons, type text, or select options on web elements
- extract: Get text, attributes, or data from the page
- screenshot: Take screenshots of the page or specific elements
- wait: Wait for elements to appear or conditions to be met

**Example Tool Usage Format:**
When you need to navigate to a website, use the navigate tool like this:
User: Go to google.com
Assistant: I'll navigate to Google for you.

When you need to interact with elements, use the interact tool properly.

**Key Guidelines:**
1. ALWAYS use the proper tool calling format - never generate code
2. Wait for pages to load after navigation before interacting with elements
3. Use CSS selectors to identify elements (e.g., "button.submit", "#search-input")
4. After using a tool, wait for the result before proceeding
5. Extract and report relevant information from pages using the extract tool

**Important Notes:**
- Each tool has specific parameters that must be provided
- The navigate tool requires a "url" parameter
- The interact tool requires "action", "selector" and sometimes "text" parameters
- The extract tool requires "selector" or "extract_type" parameters
- Never write code examples - only use the tools through the proper API

Your responses should be helpful and describe what you're doing, but the actual actions must be performed through tool calls."""

    TASK_EXECUTION_PROMPT = """Given the following task, break it down into specific, actionable steps for browser automation:

Task: {task}

Current Context:
- Current URL: {current_url}
- Page Title: {page_title}
- Available Elements: {available_elements}

Please provide:
1. A clear understanding of what needs to be accomplished
2. A step-by-step plan with specific actions
3. Expected outcomes for each step
4. Potential challenges and how to handle them

Focus on being precise with element selectors and user interactions."""

    ERROR_RECOVERY_PROMPT = """An error occurred during browser automation:

Error Type: {error_type}
Error Message: {error_message}
Failed Action: {failed_action}
Current State: {current_state}

Please analyze this error and provide:
1. Likely cause of the error
2. Alternative approaches to accomplish the same goal
3. Specific recovery steps to try
4. Whether the task should be abandoned or continued

Consider the context and try to find robust solutions that avoid similar issues."""

    ELEMENT_ANALYSIS_PROMPT = """Analyze the following web page elements and determine the best interaction strategy:

Page URL: {url}
Elements Found: {elements}
Task Context: {task_context}

For each relevant element, provide:
1. Element type and purpose
2. Best selector strategy (CSS, XPath, text content)
3. Required interaction method (click, type, select, etc.)
4. Any special considerations (timing, visibility, etc.)

Prioritize elements by relevance to the current task."""

    DATA_EXTRACTION_PROMPT = """Extract and structure the following information from the current web page:

Target Information: {target_info}
Page Content: {page_content}
Structured Data: {structured_data}

Please provide:
1. All relevant data found on the page
2. Confidence level for each piece of information
3. Source location within the page (element selector/path)
4. Suggested data validation or verification steps

Format the response as structured data (JSON) when possible."""

    @classmethod
    def get_system_prompt(cls) -> ChatPromptTemplate:
        """Get the main system prompt for OpenAI tools agent."""
        return ChatPromptTemplate.from_messages([
            ("system", cls.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
    
    @classmethod
    def get_task_prompt(cls) -> ChatPromptTemplate:
        """Get prompt for task execution planning."""
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(cls.SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(cls.TASK_EXECUTION_PROMPT)
        ])
    
    @classmethod
    def get_error_recovery_prompt(cls) -> ChatPromptTemplate:
        """Get prompt for error recovery."""
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(cls.SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(cls.ERROR_RECOVERY_PROMPT)
        ])
    
    @classmethod
    def get_element_analysis_prompt(cls) -> ChatPromptTemplate:
        """Get prompt for element analysis."""
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(cls.SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(cls.ELEMENT_ANALYSIS_PROMPT)
        ])
    
    @classmethod
    def get_extraction_prompt(cls) -> ChatPromptTemplate:
        """Get prompt for data extraction."""
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(cls.SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(cls.DATA_EXTRACTION_PROMPT)
        ])

    @classmethod
    def create_custom_prompt(
        cls,
        task_description: str,
        context: Dict[str, Any] = None
    ) -> ChatPromptTemplate:
        """
        Create a custom prompt for specific tasks.
        
        Args:
            task_description: Description of the specific task
            context: Additional context information
            
        Returns:
            ChatPromptTemplate for the custom task
        """
        context = context or {}
        
        custom_template = f"""
Task: {task_description}

Context: {context}

Please approach this task systematically:
1. Analyze the requirements and current state
2. Plan your approach step by step
3. Execute the plan using available tools
4. Verify results and provide feedback
5. Suggest next steps or optimizations

Focus on accuracy, safety, and providing clear explanations of your actions.
"""
        
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(cls.SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(custom_template)
        ])