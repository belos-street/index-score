---
name: models-integration
description: LangChain model integration for OpenAI, Anthropic, Google, and other providers
---

# Models Integration

> LangChain provides unified interface to connect to OpenAI, Anthropic, Google, and more LLM providers.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/models

## Supported Providers

- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- AWS (Bedrock)
- Azure OpenAI
- Cohere
- Hugging Face
- And more...

## Installation

```bash
pip install langchain
pip install langchain-openai
pip install langchain-anthropic
pip install langchain-google-genai
```

## OpenAI

### Basic Usage

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4")
response = model.invoke("Hello, world!")
```

### With Configuration

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-4",
    temperature=0.1,
    max_tokens=1000,
    timeout=30,
    api_key="your-api-key",
    base_url="https://api.openai.com/v1"
)
```

### Streaming

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4", streaming=True)

for chunk in model.stream("Tell me a story"):
    print(chunk.content, end="", flush=True)
```

## Anthropic

### Basic Usage

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(model="claude-sonnet-4-6")
response = model.invoke("Hello, world!")
```

### With Configuration

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model="claude-sonnet-4-6",
    temperature=0.1,
    max_tokens=1000,
    timeout=30,
    api_key="your-api-key"
)
```

## Google Gemini

### Basic Usage

```python
from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(model="gemini-pro")
response = model.invoke("Hello, world!")
```

### With Configuration

```python
from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(
    model="gemini-pro",
    temperature=0.1,
    max_tokens=1000,
    google_api_key="your-api-key"
)
```

## Azure OpenAI

```python
from langchain_openai import AzureChatOpenAI

model = AzureChatOpenAI(
    azure_deployment="your-deployment-name",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_key="your-api-key",
    api_version="2024-02-15-preview"
)
```

## Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | str | Model identifier |
| `temperature` | float | Randomness (0-2) |
| `max_tokens` | int | Maximum output tokens |
| `timeout` | int | Request timeout in seconds |
| `api_key` | str | API key (or use env var) |
| `base_url` | str | Custom API endpoint |
| `streaming` | bool | Enable streaming |

## Environment Variables

```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
```

## Model Selection in Agents

### String Shorthand

```python
from langchain.agents import create_agent

agent = create_agent("openai:gpt-4", tools=tools)
agent = create_agent("anthropic:claude-sonnet-4-6", tools=tools)
```

### Instance Injection

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4", temperature=0.1)
agent = create_agent(model, tools=tools)
```

## Best Practices

1. **Use Environment Variables**: Store API keys in env vars, not in code
2. **Set Timeouts**: Always set reasonable timeouts for production
3. **Temperature Control**: Use low temperature (0.1-0.3) for factual tasks
4. **Token Limits**: Set max_tokens to control costs
5. **Fallback Models**: Implement fallback logic for reliability

## Fallback Pattern

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

primary_model = ChatOpenAI(model="gpt-4")
fallback_model = ChatAnthropic(model="claude-sonnet-4-6")

try:
    response = primary_model.invoke(prompt)
except Exception as e:
    response = fallback_model.invoke(prompt)
```

## Cost Optimization

### Use Smaller Models for Simple Tasks

```python
fast_model = ChatOpenAI(model="gpt-4-mini")
smart_model = ChatOpenAI(model="gpt-4")

if is_simple_task(prompt):
    model = fast_model
else:
    model = smart_model
```

### Token Counting

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4")
tokens = model.get_num_tokens("Your text here")
print(f"Token count: {tokens}")
```
