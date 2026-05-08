---
name: middleware-overview
description: LangChain middleware architecture and patterns for cross-cutting concerns
---

# Middleware Overview

> Middleware provides a way to intercept and modify agent behavior, enabling cross-cutting concerns like logging, error handling, and dynamic tool selection.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/middleware

## Core Concept

Middleware wraps the agent's execution pipeline, allowing you to:
- Intercept requests and responses
- Modify state and tools dynamically
- Add logging and monitoring
- Implement error handling and retries

## Middleware Types

### wrap_model_call

Intercepts model invocations:

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def logging_middleware(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Log all model calls."""
    print(f"Model call started: {len(request.state['messages'])} messages")
    
    response = handler(request)
    
    print(f"Model call completed: {len(response.content)} chars")
    return response
```

### wrap_tool_call

Intercepts tool executions:

```python
from langchain.agents.middleware import wrap_tool_call, ToolRequest, ToolResponse

@wrap_tool_call
def tool_logging_middleware(
    request: ToolRequest,
    handler: Callable[[ToolRequest], ToolResponse]
) -> ToolResponse:
    """Log all tool calls."""
    print(f"Tool called: {request.tool_name}")
    print(f"Arguments: {request.args}")
    
    response = handler(request)
    
    print(f"Tool result: {response.content[:100]}...")
    return response
```

## Using Middleware

### Basic Setup

```python
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-4",
    tools=[get_weather, search],
    middleware=[logging_middleware, error_handling_middleware]
)
```

### Multiple Middleware

```python
agent = create_agent(
    model="gpt-4",
    tools=tools,
    middleware=[
        logging_middleware,
        rate_limit_middleware,
        error_handling_middleware,
        caching_middleware
    ]
)
```

## Built-in Middleware

### SummarizationMiddleware

Automatically summarizes old messages:

```python
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-4",
    tools=tools,
    middleware=[SummarizationMiddleware(max_messages=10)]
)
```

### HumanInTheLoopMiddleware

Adds human intervention:

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-4",
    tools=[delete_file, send_email],
    middleware=[HumanInTheLoopMiddleware(
        require_approval_for=["delete_file", "send_email"]
    )]
)
```

## Common Patterns

### Logging Middleware

```python
import logging
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

logger = logging.getLogger(__name__)

@wrap_model_call
def logging_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Comprehensive logging middleware."""
    logger.info(f"Model call started with {len(request.state['messages'])} messages")
    
    try:
        response = handler(request)
        logger.info(f"Model call completed successfully")
        return response
    except Exception as e:
        logger.error(f"Model call failed: {e}")
        raise
```

### Error Handling Middleware

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

@wrap_model_call
def error_handling_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Graceful error handling."""
    try:
        return handler(request)
    except Exception as e:
        return ModelResponse(
            content=f"An error occurred: {str(e)}. Please try again.",
            tool_calls=[]
        )
```

### Rate Limiting Middleware

```python
import time
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

@wrap_model_call
def rate_limit_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Simple rate limiting."""
    min_interval = 1.0
    
    last_call = request.state.get("last_model_call", 0)
    current_time = time.time()
    
    if current_time - last_call < min_interval:
        time.sleep(min_interval - (current_time - last_call))
    
    response = handler(request)
    request.state["last_model_call"] = time.time()
    
    return response
```

### Caching Middleware

```python
import hashlib
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

_cache = {}

@wrap_model_call
def caching_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Simple response caching."""
    cache_key = hashlib.md5(
        str(request.state["messages"]).encode()
    ).hexdigest()
    
    if cache_key in _cache:
        return _cache[cache_key]
    
    response = handler(request)
    _cache[cache_key] = response
    
    return response
```

## Modifying Requests

### Override Model

```python
@wrap_model_call
def dynamic_model_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Switch model based on task complexity."""
    messages = request.state["messages"]
    last_msg = messages[-1].content
    
    if "complex" in last_msg.lower():
        model = ChatOpenAI(model="gpt-4")
    else:
        model = ChatOpenAI(model="gpt-4-mini")
    
    return handler(request.override(model=model))
```

### Override Tools

```python
@wrap_model_call
def filter_tools_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Filter tools based on user permissions."""
    user_role = request.state.get("user_role", "user")
    
    if user_role == "admin":
        tools = request.tools
    else:
        tools = [t for t in request.tools if t.name != "delete_file"]
    
    return handler(request.override(tools=tools))
```

### Modify State

```python
@wrap_model_call
def state_enrichment_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Add context to state."""
    state = request.state
    state["timestamp"] = time.time()
    state["user_id"] = get_current_user_id()
    
    return handler(request.override(state=state))
```

## Best Practices

1. **Keep Middleware Focused**: Each middleware should do one thing
2. **Order Matters**: Middleware executes in order, place logging first
3. **Handle Errors**: Always wrap handler calls in try-except
4. **Use State Wisely**: Store cross-cutting data in state
5. **Test Thoroughly**: Middleware affects all agent calls

## Advanced Patterns

### Conditional Middleware

```python
@wrap_model_call
def conditional_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Apply logic only in certain conditions."""
    if should_apply_logic(request):
        return custom_logic(request, handler)
    else:
        return handler(request)
```

### Middleware Composition

```python
def compose_middleware(*middlewares):
    """Compose multiple middleware into one."""
    @wrap_model_call
    def composed(request: ModelRequest, handler) -> ModelResponse:
        def apply_middlewares(i, req):
            if i >= len(middlewares):
                return handler(req)
            return middlewares[i](req, lambda r: apply_middlewares(i + 1, r))
        
        return apply_middlewares(0, request)
    
    return composed

agent = create_agent(
    model="gpt-4",
    tools=tools,
    middleware=[compose_middleware(
        logging_middleware,
        error_handling_middleware
    )]
)
```
