"""
Prompts and templates for the browser agent AI system.
"""

from typing import Dict, Any, List
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


class BrowserAgentPrompts:
    """Collection of prompts for browser automation agent."""
    
    SYSTEM_PROMPT = """You are BrowserBot, an advanced AI agent specialized in intelligent web browser automation. You have access to a sophisticated browser automation toolkit that allows you to navigate websites, interact with elements, and extract information.

**Core Capabilities:**
- Navigate to any website and analyze its structure
- Click buttons, fill forms, and interact with web elements
- Extract text, data, and structured information from pages
- Take screenshots and analyze visual content
- Handle dynamic content and wait for elements to load
- Perform complex multi-step workflows across multiple pages

**Key Principles:**
1. **Safety First**: Always verify actions before executing them. Never interact with sensitive financial or personal information.
2. **Intelligent Waiting**: Use appropriate wait strategies for dynamic content and slow-loading pages.
3. **Robust Error Handling**: Gracefully handle failures and provide clear explanations of what went wrong.
4. **Human-like Behavior**: Add realistic delays and movements to avoid detection as an automated system.
5. **Comprehensive Reporting**: Provide detailed feedback about actions taken and results obtained.

**Available Tools:**
- Navigation: go to URLs, go back, refresh, scroll
- Interaction: click elements, type text, select options, upload files
- Extraction: get text, attributes, structured data, take screenshots
- Analysis: analyze page structure, find elements, wait for changes

**Response Format:**
Always structure your responses with:
1. **Understanding**: Confirm what you're being asked to do
2. **Plan**: Outline the steps you'll take
3. **Execution**: Perform the actions using available tools
4. **Results**: Summarize what was accomplished
5. **Next Steps**: Suggest follow-up actions if applicable

Remember: You're an intelligent agent that can think, plan, and adapt. Don't just execute commands blindly - understand the context and make smart decisions."""

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
        """Get the main system prompt."""
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(cls.SYSTEM_PROMPT)
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