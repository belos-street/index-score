---
name: messages-format
description: LangChain message formats and conversation structure
---

# Messages Format

> Messages are the fundamental unit of communication in LangChain, representing the conversation between users, assistants, and tools.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/messages

## Message Types

### SystemMessage

Sets the behavior and context for the assistant:

```python
from langchain_core.messages import SystemMessage

system_msg = SystemMessage(content="You are a helpful assistant.")
```

### HumanMessage

User input to the conversation:

```python
from langchain_core.messages import HumanMessage

user_msg = HumanMessage(content="What is the weather in SF?")
```

### AIMessage

Assistant's response:

```python
from langchain_core.messages import AIMessage

ai_msg = AIMessage(content="The weather in SF is sunny and 72°F.")
```

### ToolMessage

Tool execution results:

```python
from langchain_core.messages import ToolMessage

tool_msg = ToolMessage(
    content="Temperature: 72°F, Condition: Sunny",
    tool_call_id="call_123"
)
```

## Conversation Structure

### Basic Conversation

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is the capital of France?"),
    AIMessage(content="The capital of France is Paris."),
    HumanMessage(content="What about Germany?"),
]
```

### Using Dict Format

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "The capital of France is Paris."},
    {"role": "user", "content": "What about Germany?"},
]
```

## Message Properties

### Common Properties

```python
from langchain_core.messages import HumanMessage

msg = HumanMessage(
    content="Hello",
    additional_kwargs={
        "timestamp": "2024-01-01T00:00:00Z",
        "user_id": "user123"
    }
)

print(msg.content)
print(msg.type)
print(msg.additional_kwargs)
```

### AIMessage with Tool Calls

```python
from langchain_core.messages import AIMessage

ai_msg = AIMessage(
    content="",
    tool_calls=[
        {
            "name": "get_weather",
            "args": {"city": "San Francisco"},
            "id": "call_123"
        }
    ]
)
```

## Working with Messages

### Accessing Content

```python
from langchain_core.messages import HumanMessage

msg = HumanMessage(content="Hello")
print(msg.content)
```

### Message Type Checking

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def process_message(msg):
    if isinstance(msg, HumanMessage):
        print(f"User said: {msg.content}")
    elif isinstance(msg, AIMessage):
        print(f"Assistant said: {msg.content}")
    elif isinstance(msg, SystemMessage):
        print(f"System: {msg.content}")
```

### Converting to Dict

```python
from langchain_core.messages import HumanMessage

msg = HumanMessage(content="Hello")
msg_dict = msg.dict()
print(msg_dict)
```

## Message History

### Adding to History

```python
from langchain_core.messages import HumanMessage, AIMessage

history = []

history.append(HumanMessage(content="Hello"))
history.append(AIMessage(content="Hi! How can I help you?"))
history.append(HumanMessage(content="What's the weather?"))
```

### Truncating History

```python
def truncate_history(messages, max_messages=10):
    if len(messages) > max_messages:
        return messages[-max_messages:]
    return messages
```

## Best Practices

1. **Always Include System Message**: Set the context and behavior
2. **Use Dict Format**: Simpler for most use cases
3. **Track Message Order**: Maintain chronological order
4. **Handle Tool Messages**: Include tool results in conversation
5. **Limit History**: Prevent context overflow

## Common Patterns

### Chat Loop

```python
from langchain_core.messages import HumanMessage, AIMessage

messages = [
    {"role": "system", "content": "You are a helpful assistant."}
]

while True:
    user_input = input("You: ")
    messages.append({"role": "user", "content": user_input})
    
    response = model.invoke(messages)
    messages.append({"role": "assistant", "content": response.content})
    
    print(f"Assistant: {response.content}")
```

### Multi-Modal Messages

```python
from langchain_core.messages import HumanMessage

msg = HumanMessage(
    content=[
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
    ]
)
```

### Message Serialization

```python
import json
from langchain_core.messages import HumanMessage, AIMessage

messages = [
    HumanMessage(content="Hello"),
    AIMessage(content="Hi!")
]

serialized = [msg.dict() for msg in messages]
json_str = json.dumps(serialized)

deserialized = [HumanMessage(**msg) if msg["type"] == "human" else AIMessage(**msg) 
                for msg in json.loads(json_str)]
```
