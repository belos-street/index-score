---
name: streaming-output
description: LangChain streaming output for real-time responses
---

# Streaming Output

> Streaming provides real-time responses, improving user experience by showing content as it's generated.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/streaming

## Basic Streaming

### Enable Streaming

```python
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-4",
    tools=[get_weather],
    streaming=True
)
```

### Stream Method

```python
async for chunk in agent.stream({"messages": [...]}):
    print(chunk.content, end="", flush=True)
```

## Model Streaming

### OpenAI Streaming

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4", streaming=True)

for chunk in model.stream("Tell me a story"):
    print(chunk.content, end="", flush=True)
```

### Anthropic Streaming

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(model="claude-sonnet-4-6", streaming=True)

for chunk in model.stream("Tell me a story"):
    print(chunk.content, end="", flush=True)
```

## Async Streaming

### Async Iterator

```python
import asyncio
from langchain_openai import ChatOpenAI

async def stream_response():
    model = ChatOpenAI(model="gpt-4", streaming=True)
    
    async for chunk in model.astream("Tell me a story"):
        print(chunk.content, end="", flush=True)

asyncio.run(stream_response())
```

### Async with Agent

```python
import asyncio
from langchain.agents import create_agent

async def stream_agent():
    agent = create_agent(model="gpt-4", tools=tools, streaming=True)
    
    async for chunk in agent.astream({"messages": [...]}):
        print(chunk.content, end="", flush=True)

asyncio.run(stream_agent())
```

## Stream Events

### Event Types

```python
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

handler = StreamingStdOutCallbackHandler()

model = ChatOpenAI(
    model="gpt-4",
    streaming=True,
    callbacks=[handler]
)
```

### Custom Callback Handler

```python
from langchain.callbacks.base import BaseCallbackHandler

class MyStreamingHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"Token: {token}")
    
    def on_llm_start(self, serialized, prompts, **kwargs) -> None:
        print("Generation started")
    
    def on_llm_end(self, response, **kwargs) -> None:
        print("Generation completed")

model = ChatOpenAI(
    model="gpt-4",
    streaming=True,
    callbacks=[MyStreamingHandler()]
)
```

## Streaming with Tools

### Tool Call Streaming

```python
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-4",
    tools=[search, get_weather],
    streaming=True
)

async for event in agent.astream_events({"messages": [...]}):
    if event["event"] == "on_tool_start":
        print(f"Tool started: {event['name']}")
    elif event["event"] == "on_tool_end":
        print(f"Tool completed: {event['name']}")
    elif event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="", flush=True)
```

## Stream Processing

### Accumulate Content

```python
async def stream_and_accumulate():
    agent = create_agent(model="gpt-4", tools=tools, streaming=True)
    
    full_content = ""
    async for chunk in agent.astream({"messages": [...]}):
        full_content += chunk.content
        print(chunk.content, end="", flush=True)
    
    print(f"\n\nFull response: {full_content}")
```

### Process Tokens

```python
import asyncio

async def process_tokens():
    model = ChatOpenAI(model="gpt-4", streaming=True)
    
    word_buffer = ""
    async for chunk in model.astream("Tell me a story"):
        word_buffer += chunk.content
        
        if chunk.content in [" ", "\n"]:
            print(f"Word: {word_buffer.strip()}")
            word_buffer = ""
```

## Web Framework Integration

### FastAPI Streaming

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI

app = FastAPI()

@app.get("/stream")
async def stream_endpoint():
    model = ChatOpenAI(model="gpt-4", streaming=True)
    
    async def generate():
        async for chunk in model.astream("Tell me a story"):
            yield f"data: {chunk.content}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Flask Streaming

```python
from flask import Flask, Response
from langchain_openai import ChatOpenAI

app = Flask(__name__)

@app.route("/stream")
def stream():
    model = ChatOpenAI(model="gpt-4", streaming=True)
    
    def generate():
        for chunk in model.stream("Tell me a story"):
            yield f"data: {chunk.content}\n\n"
    
    return Response(generate(), mimetype="text/event-stream")
```

## Best Practices

1. **Use Async**: Async streaming is more efficient for web applications
2. **Handle Errors**: Wrap streaming in try-except for robustness
3. **Set Timeouts**: Prevent hanging on slow streams
4. **Buffer Management**: Manage token buffers for word/sentence processing
5. **User Feedback**: Show loading indicators during tool execution

## Common Patterns

### Streaming with Progress

```python
async def stream_with_progress():
    agent = create_agent(model="gpt-4", tools=tools, streaming=True)
    
    print("Thinking...", end="", flush=True)
    
    async for event in agent.astream_events({"messages": [...]}):
        if event["event"] == "on_tool_start":
            print(f"\nUsing tool: {event['name']}")
        elif event["event"] == "on_chat_model_stream":
            print(event["data"]["chunk"].content, end="", flush=True)
```

### Streaming with Timeout

```python
import asyncio

async def stream_with_timeout():
    agent = create_agent(model="gpt-4", tools=tools, streaming=True)
    
    try:
        async for chunk in agent.astream({"messages": [...]}):
            print(chunk.content, end="", flush=True)
    except asyncio.TimeoutError:
        print("\n\nGeneration timed out")
```

### Streaming to File

```python
async def stream_to_file(filename: str):
    agent = create_agent(model="gpt-4", tools=tools, streaming=True)
    
    with open(filename, "w") as f:
        async for chunk in agent.astream({"messages": [...]}):
            f.write(chunk.content)
            print(chunk.content, end="", flush=True)
```
