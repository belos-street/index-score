---
name: agents-tools
description: LangChain tool definition and dynamic tool selection patterns
---

# Agents Tools

> Tools give agents the ability to take actions. Agents can call multiple tools in sequence, parallel, and handle errors gracefully.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/tools

## Tool Definition

### Using @tool Decorator

```python
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    return f"Weather in {city}: Sunny, 72°F"

@tool
def search(query: str) -> str:
    """Search for information on the web."""
    return f"Results for: {query}"
```

### Tool with Multiple Parameters

```python
from langchain.tools import tool

@tool
def calculate(operation: str, a: float, b: float) -> float:
    """Perform a calculation.
    
    Args:
        operation: One of 'add', 'subtract', 'multiply', 'divide'
        a: First number
        b: Second number
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a / b
```

### Tool with Optional Parameters

```python
from langchain.tools import tool
from typing import Optional

@tool
def search(
    query: str,
    num_results: Optional[int] = 5,
    include_images: Optional[bool] = False
) -> str:
    """Search for information.
    
    Args:
        query: Search query
        num_results: Number of results to return (default: 5)
        include_images: Whether to include images (default: False)
    """
    return f"Found {num_results} results for '{query}'"
```

## Static Tools

Tools defined at agent creation and remain unchanged:

```python
from langchain.tools import tool
from langchain.agents import create_agent

@tool
def get_weather(location: str) -> str:
    """Get weather information for a location."""
    return f"Weather in {location}: Sunny, 72°F"

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

agent = create_agent(
    model="gpt-4",
    tools=[get_weather, search]
)
```

## Dynamic Tools

### Filtering Pre-registered Tools

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def state_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on conversation state."""
    state = request.state
    is_authenticated = state.get("authenticated", False)
    
    all_tools = request.tools
    
    if is_authenticated:
        allowed_tools = all_tools
    else:
        allowed_tools = [t for t in all_tools if t.name in ["search", "get_weather"]]
    
    return handler(request.override(tools=allowed_tools))

agent = create_agent(
    model="gpt-4",
    tools=[search, get_weather, send_email, delete_file],
    middleware=[state_based_tools]
)
```

### Runtime Tool Registration

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

@wrap_model_call
def runtime_tool_registration(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Dynamically add tools at runtime."""
    state = request.state
    user_tier = state.get("user_tier", "free")
    
    tools = list(request.tools)
    
    if user_tier == "premium":
        from my_tools import advanced_analytics
        tools.append(advanced_analytics)
    
    return handler(request.override(tools=tools))
```

## Tool Execution

### Tool Retry Logic

```python
from langchain.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

@tool
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def unreliable_api_call(query: str) -> str:
    """Call an unreliable API with retry logic."""
    return api_client.call(query)
```

### Error Handling in Tools

```python
from langchain.tools import tool

@tool
def divide(a: float, b: float) -> str:
    """Divide two numbers.
    
    Returns error message if division by zero.
    """
    try:
        result = a / b
        return f"Result: {result}"
    except ZeroDivisionError:
        return "Error: Cannot divide by zero"
```

## Tool Best Practices

1. **Clear Docstrings**: Tools use docstrings for descriptions
2. **Type Hints**: Always include type hints for parameters
3. **Return Strings**: Tools should return string results
4. **Error Handling**: Return error messages, don't raise exceptions
5. **Idempotency**: Design tools to be safely re-executed

## Tool Input Schema

### Automatic Schema Generation

```python
from langchain.tools import tool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results")

@tool(args_schema=SearchInput)
def search(query: str, num_results: int = 5) -> str:
    """Search for information."""
    return f"Found {num_results} results for '{query}'"
```

## Common Patterns

### Tool with External API

```python
from langchain.tools import tool
import requests

@tool
def get_stock_price(symbol: str) -> str:
    """Get current stock price for a symbol."""
    try:
        response = requests.get(f"https://api.example.com/stock/{symbol}")
        data = response.json()
        return f"Stock {symbol}: ${data['price']}"
    except Exception as e:
        return f"Error fetching stock price: {str(e)}"
```

### Tool with State

```python
from langchain.tools import tool

_user_data = {}

@tool
def save_preference(key: str, value: str) -> str:
    """Save a user preference."""
    _user_data[key] = value
    return f"Saved {key}={value}"

@tool
def get_preference(key: str) -> str:
    """Get a user preference."""
    return _user_data.get(key, "Not found")
```

### Tool Composition

```python
from langchain.tools import tool

@tool
def search_and_summarize(query: str) -> str:
    """Search and summarize results."""
    results = search(query)
    summary = summarize(results)
    return summary
```
