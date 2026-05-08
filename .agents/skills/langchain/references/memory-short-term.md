---
name: memory-short-term
description: LangChain short-term memory and conversation context management
---

# Memory - Short Term

> Short-term memory allows agents to maintain context across a conversation, remembering previous interactions.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/short-term-memory

## Core Concept

Short-term memory stores the conversation history, enabling:
- Context-aware responses
- Multi-turn conversations
- Reference to previous messages

## Basic Usage

### Automatic Memory in Agents

Agents automatically maintain conversation state:

```python
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-4",
    tools=[get_weather]
)

result1 = agent.invoke({"messages": [{"role": "user", "content": "My name is Alice"}]})
result2 = agent.invoke({"messages": [{"role": "user", "content": "What's my name?"}]})

print(result2["messages"][-1].content)
```

### Manual Message History

```python
from langchain_core.messages import HumanMessage, AIMessage

messages = [
    HumanMessage(content="My name is Alice"),
    AIMessage(content="Hello Alice! How can I help you?"),
    HumanMessage(content="What's my name?"),
]

response = model.invoke(messages)
```

## Memory Management

### Truncating History

Prevent context overflow by limiting message count:

```python
def truncate_messages(messages, max_messages=10):
    """Keep only the most recent messages."""
    if len(messages) > max_messages:
        return messages[-max_messages:]
    return messages

messages = truncate_messages(messages, max_messages=10)
```

### Token-Based Truncation

Truncate based on token count:

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4")

def truncate_by_tokens(messages, max_tokens=4000):
    """Truncate messages to fit within token limit."""
    total_tokens = 0
    truncated = []
    
    for msg in reversed(messages):
        msg_tokens = model.get_num_tokens(msg.content)
        if total_tokens + msg_tokens > max_tokens:
            break
        truncated.insert(0, msg)
        total_tokens += msg_tokens
    
    return truncated
```

### Summarization

Compress old messages into a summary:

```python
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-4",
    tools=tools,
    middleware=[SummarizationMiddleware(max_messages=10)]
)
```

## Conversation State

### Accessing State

```python
from langchain.agents import create_agent

agent = create_agent(model="gpt-4", tools=tools)

result = agent.invoke({"messages": [...]})

state = result["state"]
messages = state["messages"]
print(f"Total messages: {len(messages)}")
```

### Modifying State

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

@wrap_model_call
def modify_state(request: ModelRequest, handler) -> ModelResponse:
    """Modify conversation state."""
    state = request.state
    
    state["user_preferences"] = {"language": "en"}
    
    return handler(request.override(state=state))
```

## Memory Patterns

### Conversation with Context

```python
from langchain_core.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="I'm planning a trip to Paris."),
]

response1 = model.invoke(messages)
messages.append(response1)

messages.append(HumanMessage(content="What should I pack?"))
response2 = model.invoke(messages)
```

### Multi-Session Memory

```python
import json
from langchain_core.messages import HumanMessage, AIMessage

class ConversationMemory:
    def __init__(self):
        self.sessions = {}
    
    def save_session(self, session_id: str, messages: list):
        self.sessions[session_id] = [msg.dict() for msg in messages]
    
    def load_session(self, session_id: str) -> list:
        data = self.sessions.get(session_id, [])
        return [HumanMessage(**msg) if msg["type"] == "human" else AIMessage(**msg) 
                for msg in data]

memory = ConversationMemory()

messages = [HumanMessage(content="Hello")]
memory.save_session("user123", messages)
```

## Best Practices

1. **Limit History**: Prevent context overflow (10-20 messages typically)
2. **Use Summarization**: Compress old messages automatically
3. **Persist Important Info**: Extract and store key information separately
4. **Token Awareness**: Monitor token usage for cost control
5. **Session Management**: Use session IDs for multi-user applications

## Common Issues

### Context Overflow

**Problem**: Too many messages exceed model's context window.

**Solution**:
```python
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-4",
    tools=tools,
    middleware=[SummarizationMiddleware(max_messages=10)]
)
```

### Lost Context

**Problem**: Important information gets truncated.

**Solution**: Extract and store key information in state:
```python
@wrap_model_call
def extract_important_info(request: ModelRequest, handler) -> ModelResponse:
    response = handler(request)
    
    state = request.state
    last_user_msg = [m for m in state["messages"] if m.type == "human"][-1]
    
    if "my name is" in last_user_msg.content.lower():
        state["user_name"] = extract_name(last_user_msg.content)
    
    return response
```

## Advanced Patterns

### Sliding Window Memory

```python
def sliding_window_memory(messages, window_size=5):
    """Keep system message + last N exchanges."""
    system_messages = [m for m in messages if m.type == "system"]
    other_messages = [m for m in messages if m.type != "system"]
    
    return system_messages + other_messages[-window_size*2:]
```

### Priority-Based Memory

```python
def priority_memory(messages, max_messages=10):
    """Keep important messages (questions, decisions) over chitchat."""
    scored = []
    for msg in messages:
        score = 0
        if "?" in msg.content:
            score += 2
        if any(word in msg.content.lower() for word in ["important", "remember", "save"]):
            score += 3
        scored.append((msg, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return [msg for msg, score in scored[:max_messages]]
```
