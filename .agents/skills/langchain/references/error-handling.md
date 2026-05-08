---
name: error-handling
description: Production error handling patterns for LangChain agents
---

# Error Handling

> Robust error handling ensures agents fail gracefully and can recover from errors in production.

**Official Docs**: https://docs.langchain.com/oss/python/langchain

## Common Errors

### API Errors

```python
from openai import APIError, RateLimitError, APIConnectionError
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4")

try:
    response = model.invoke("Hello")
except RateLimitError:
    print("Rate limit exceeded, please wait")
except APIConnectionError:
    print("Failed to connect to OpenAI")
except APIError as e:
    print(f"OpenAI API error: {e}")
```

### Tool Errors

```python
from langchain.tools import tool

@tool
def divide(a: float, b: float) -> str:
    """Divide two numbers."""
    try:
        result = a / b
        return f"Result: {result}"
    except ZeroDivisionError:
        return "Error: Cannot divide by zero"
    except Exception as e:
        return f"Error: {str(e)}"
```

## Error Handling Strategies

### Try-Catch in Tools

```python
from langchain.tools import tool
import requests

@tool
def fetch_url(url: str) -> str:
    """Fetch content from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text[:1000]
    except requests.Timeout:
        return "Error: Request timed out"
    except requests.ConnectionError:
        return "Error: Failed to connect to URL"
    except requests.HTTPError as e:
        return f"Error: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_openai import ChatOpenAI

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def call_model_with_retry(prompt: str):
    model = ChatOpenAI(model="gpt-4")
    return model.invoke(prompt)
```

### Fallback Models

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

primary_model = ChatOpenAI(model="gpt-4")
fallback_model = ChatAnthropic(model="claude-sonnet-4-6")

def call_with_fallback(prompt: str):
    try:
        return primary_model.invoke(prompt)
    except Exception as e:
        print(f"Primary model failed: {e}, using fallback")
        return fallback_model.invoke(prompt)
```

## Middleware Error Handling

### Global Error Handler

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

@wrap_model_call
def error_handling_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Global error handling middleware."""
    try:
        return handler(request)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        
        return ModelResponse(
            content=error_message,
            tool_calls=[]
        )
```

### Error Logging

```python
import logging
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

logger = logging.getLogger(__name__)

@wrap_model_call
def logging_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Log errors with context."""
    try:
        return handler(request)
    except Exception as e:
        logger.error(
            f"Error in model call",
            extra={
                "error": str(e),
                "messages": len(request.state.get("messages", [])),
                "tools": [t.name for t in request.tools]
            },
            exc_info=True
        )
        raise
```

## Tool Error Recovery

### Graceful Degradation

```python
from langchain.tools import tool

@tool
def search_with_fallback(query: str) -> str:
    """Search with fallback to simpler search."""
    try:
        return advanced_search(query)
    except Exception:
        try:
            return simple_search(query)
        except Exception:
            return "Search temporarily unavailable"
```

### Error Context

```python
from langchain.tools import tool

@tool
def api_call(endpoint: str) -> str:
    """Make API call with detailed error context."""
    try:
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return f"Error: Request to {endpoint} timed out after 10s"
    except requests.HTTPError as e:
        return f"Error: {endpoint} returned {e.response.status_code}"
    except Exception as e:
        return f"Error: Failed to call {endpoint} - {str(e)}"
```

## Validation Errors

### Input Validation

```python
from pydantic import BaseModel, ValidationError, Field

class ToolInput(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    num_results: int = Field(ge=1, le=100)

def validate_input(data: dict):
    try:
        return ToolInput(**data)
    except ValidationError as e:
        return f"Validation error: {e}"
```

### Output Validation

```python
from pydantic import BaseModel, ValidationError

class Person(BaseModel):
    name: str
    age: int

def parse_person(data: str):
    try:
        return Person.model_validate_json(data)
    except ValidationError as e:
        print(f"Invalid person data: {e}")
        return None
```

## Timeout Handling

### Request Timeout

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-4",
    timeout=30,
    max_retries=2
)
```

### Tool Timeout

```python
from langchain.tools import tool
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

@tool
def long_running_task() -> str:
    """Task with timeout."""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)
    
    try:
        result = perform_task()
        signal.alarm(0)
        return result
    except TimeoutError:
        return "Error: Task timed out after 30 seconds"
```

## Circuit Breaker Pattern

```python
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"
    
    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self.failures = 0
            self.state = "closed"
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            if self.failures >= self.failure_threshold:
                self.state = "open"
            
            raise

circuit_breaker = CircuitBreaker()

@tool
def reliable_api_call(query: str) -> str:
    """API call with circuit breaker."""
    try:
        return circuit_breaker.call(api_call, query)
    except Exception as e:
        return f"Error: {str(e)}"
```

## Best Practices

1. **Always Handle Errors**: Never let errors propagate silently
2. **Provide Context**: Include error details in messages
3. **Log Errors**: Log errors with context for debugging
4. **Use Retries**: Retry transient errors with exponential backoff
5. **Implement Fallbacks**: Have backup strategies for critical operations
6. **Set Timeouts**: Prevent hanging on slow operations
7. **Validate Inputs**: Check inputs before processing

## Common Patterns

### Comprehensive Error Handler

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
import logging

logger = logging.getLogger(__name__)

@wrap_model_call
def comprehensive_error_handler(request: ModelRequest, handler) -> ModelResponse:
    """Comprehensive error handling with logging and recovery."""
    try:
        return handler(request)
    except RateLimitError:
        logger.warning("Rate limit hit")
        return ModelResponse(
            content="Rate limit reached. Please try again in a moment.",
            tool_calls=[]
        )
    except APIConnectionError:
        logger.error("API connection failed")
        return ModelResponse(
            content="Unable to connect to the AI service. Please check your connection.",
            tool_calls=[]
        )
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return ModelResponse(
            content=f"Invalid input: {str(e)}",
            tool_calls=[]
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return ModelResponse(
            content="An unexpected error occurred. Please try again.",
            tool_calls=[]
        )
```

### Error Recovery Agent

```python
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-4",
    tools=[search, api_call],
    middleware=[
        error_handling_middleware,
        logging_middleware,
        retry_middleware
    ],
    max_retries=3
)
```
