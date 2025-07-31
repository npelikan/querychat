"""
Utilities for testing QueryChat examples.

This module provides mock objects and helpers for testing QueryChat without
requiring actual LLM access, ensuring tests are reproducible.
"""

from typing import Dict, Optional
import pandas as pd


class MockStreamResponse:
    """Mock for chatlas stream response."""

    def __init__(self, content: str):
        self.content = content
        self._chunks = content.split()
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk

    def get_content(self):
        """Get the full content."""
        return self.content


class MockChat:
    """Mock for chatlas.Chat class."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize a mock Chat object.
        
        Args:
            responses: A dictionary mapping prompts to responses
        """
        self.responses = responses or {}
        self.default_response = "I'm a mock response from MockChat."
        self.calls = []
        self.tools = {}

    def register_tool(self, tool_func):
        """Mock register_tool method."""
        self.tools[tool_func.__name__] = tool_func
        
    def add_response(self, prompt: str, response: str):
        """Add a response for a specific prompt."""
        self.responses[prompt] = response

    async def stream_async(self, prompt: str, echo: str = "none"):
        """Mock stream_async method."""
        self.calls.append({"prompt": prompt, "echo": echo})
        response = self.responses.get(prompt, self.default_response)
        return MockStreamResponse(response)

    async def call_async(self, prompt: str, echo: str = "none"):
        """Mock call_async method."""
        self.calls.append({"prompt": prompt, "echo": echo})
        response = self.responses.get(prompt, self.default_response)
        return response


class MockSQLQueryChat(MockChat):
    """Mock Chat specialized for SQL queries."""
    
    def __init__(self, responses: Optional[Dict[str, str]] = None, 
                 data: Optional[pd.DataFrame] = None, 
                 sql_responses: Optional[Dict[str, str]] = None):
        """
        Initialize a mock Chat object that can return SQL queries.
        
        Args:
            responses: A dictionary mapping prompts to responses
            data: The dataframe to use for data-based responses
            sql_responses: A dictionary mapping prompts to SQL queries
        """
        super().__init__(responses)
        self.data = data if data is not None else pd.DataFrame()
        self.sql_responses = sql_responses or {}
        
    async def stream_async(self, prompt: str, echo: str = "none"):
        """Mock stream_async that can generate SQL and update tool calls."""
        self.calls.append({"prompt": prompt, "echo": echo})
        
        # If this is a greeting request
        if "greeting" in prompt.lower() or "Include a few sample prompts" in prompt:
            response = self.responses.get(prompt, "👋 Welcome to the mock chat! Try asking: \n* Show me the data\n* Filter for high values")
            return MockStreamResponse(response)
            
        # If there's a specific SQL response for this prompt, use it
        if prompt in self.sql_responses:
            sql = self.sql_responses[prompt]
            
            # If there's an update_dashboard tool, call it
            if "update_dashboard" in self.tools:
                title = f"Query: {prompt}"
                await self.tools["update_dashboard"](sql, title)
                
            # Return a response that mentions the SQL
            response = f"I've created this SQL query to answer your question:\n\n```sql\n{sql}\n```"
            return MockStreamResponse(response)
        
        # Default fallback response
        return MockStreamResponse(self.default_response)


def create_mock_sql_chat(data: pd.DataFrame, sql_mapping: Dict[str, str]) -> MockSQLQueryChat:
    """
    Create a mock SQL chat configured with data and responses.
    
    Args:
        data: DataFrame to use for responses
        sql_mapping: Dictionary mapping prompts to SQL queries
        
    Returns:
        A mock chat ready for testing
    """
    # Create standard responses
    responses = {
        "Please give me a friendly greeting.": "👋 Welcome to the mock chat! Try asking questions about the data.",
        "Please give me a friendly greeting. Include a few sample prompts in a two-level bulleted list.": 
            "👋 Welcome! Here are some questions you can ask:\n\n* About the data\n  * Show me the first 5 rows\n  * What columns are available?\n* Analysis\n  * Calculate summary statistics\n  * Are there any missing values?"
    }
    
    return MockSQLQueryChat(responses=responses, data=data, sql_responses=sql_mapping)


def mock_chatlas_factory(mock_chat):
    """Factory function to create mock chatlas module with preconfigured Chat."""
    class MockChatFactory:
        def __init__(self, model=None, system_prompt=None, api_key=None, **kwargs):
            # Store any kwargs but don't require api_key
            self.model = model
            self.system_prompt = system_prompt
            self.kwargs = kwargs
        
        def __call__(self, system_prompt: Optional[str] = "") -> MockChat:
            # If system_prompt is provided here, update the stored one
            if system_prompt:
                self.system_prompt = system_prompt
            return mock_chat
    
    return MockChatFactory