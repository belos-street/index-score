---
name: agents-basics
description: LangChain agent architecture and create_agent usage patterns
---

# Agents Basics

> Agents combine language models with tools to create systems that can reason about tasks, decide which tools to use, and iteratively work towards solutions.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/agents

## Core Concept

An agent runs in a loop:
1. Receives input/messages
2. Decides which tools to use (if any)
3. Executes tools
4. Processes results
5. Continues until stop condition (final output or iteration limit)

## Basic Usage

### Simple Agent

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)
```

### Agent with Model Instance

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-4",
    temperature=0.1,
    max_tokens=1000,
    timeout=30
)

agent = create_agent(model, tools=[get_weather])
```

## Model Configuration

### Static Model

Models configured once and remain unchanged:

```python
from langchain.agents import create_agent

agent = create_agent("openai:gpt-4", tools=tools)
```

### Dynamic Model Selection

Models selected at runtime based on context:

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

basic_model = ChatOpenAI(model="gpt-4-mini")
advanced_model = ChatOpenAI(model="gpt-4")

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """Choose model based on conversation complexity."""
    message_count = len(request.state["messages"])
    
    if message_count > 10:
        model = advanced_model
    else:
        model = basic_model
    
    return handler(request.override(model=model))

agent = create_agent(
    model=basic_model,
    tools=tools,
    middleware=[dynamic_model_selection]
)
```

## Agent Execution

### Invoke (Blocking)

```python
result = agent.invoke({"messages": [...]})
print(result["messages"][-1].content)
```

### Stream (Async)

```python
async for chunk in agent.stream({"messages": [...]}):
    print(chunk.content, end="", flush=True)
```

### Batch Processing

```python
results = agent.batch([
    {"messages": [{"role": "user", "content": "query 1"}]},
    {"messages": [{"role": "user", "content": "query 2"}]},
])
```

## Key Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | str or Model | LLM model (string or instance) |
| `tools` | List[Tool] | List of tools available to agent |
| `system_prompt` | str | System message for the agent |
| `middleware` | List[Middleware] | Middleware functions |
| `output_schema` | BaseModel | Structured output schema |
| `streaming` | bool | Enable streaming output |

## Best Practices

1. **Start Simple**: Use string model names for quick prototyping
2. **Use Model Instances**: When you need fine-grained control (temperature, timeout, etc.)
3. **Dynamic Selection**: Use middleware for cost optimization and routing
4. **Error Handling**: Always wrap agent calls in try-except
5. **Iteration Limits**: Set reasonable limits to prevent infinite loops

## Common Patterns

### Tool-Heavy Agent

```python
agent = create_agent(
    model="gpt-4",
    tools=[search, get_weather, calculate, send_email],
    system_prompt="You are a helpful assistant with access to multiple tools."
)
```

### Cost-Optimized Agent

```python
agent = create_agent(
    model="gpt-4-mini",
    tools=tools,
    middleware=[dynamic_model_selection]
)
```

### Production Agent

```python
agent = create_agent(
    model=ChatOpenAI(model="gpt-4", timeout=30),
    tools=tools,
    middleware=[
        error_handling_middleware,
        logging_middleware,
        rate_limit_middleware
    ]
)
```
