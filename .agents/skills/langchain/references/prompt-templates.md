---
name: prompt-templates
description: LangChain prompt templates for reusable and dynamic prompts
---

# Prompt Templates

> Prompt templates enable reusable, dynamic prompts with variable substitution and composition.

## Basic Usage

### String Template

```python
from langchain.prompts import PromptTemplate

template = PromptTemplate.from_template("Tell me a joke about {topic}")

prompt = template.format(topic="AI")
print(prompt)
```

### Chat Prompt Template

```python
from langchain.prompts import ChatPromptTemplate

template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("user", "Tell me about {topic}")
])

messages = template.format_messages(topic="Python")
```

## Template Variables

### Single Variable

```python
from langchain.prompts import PromptTemplate

template = PromptTemplate(
    template="What is the capital of {country}?",
    input_variables=["country"]
)

prompt = template.format(country="France")
```

### Multiple Variables

```python
from langchain.prompts import PromptTemplate

template = PromptTemplate(
    template="Translate {text} from {source_lang} to {target_lang}",
    input_variables=["text", "source_lang", "target_lang"]
)

prompt = template.format(
    text="Hello",
    source_lang="English",
    target_lang="French"
)
```

### Partial Variables

```python
from langchain.prompts import PromptTemplate

template = PromptTemplate(
    template="Hello {name}, welcome to {place}!",
    input_variables=["name", "place"]
)

partial_template = template.partial(place="Paris")
prompt = partial_template.format(name="Alice")
```

## Chat Templates

### System + User Messages

```python
from langchain.prompts import ChatPromptTemplate

template = ChatPromptTemplate.from_messages([
    ("system", "You are a {role} assistant."),
    ("user", "{question}")
])

messages = template.format_messages(
    role="helpful",
    question="What is AI?"
)
```

### With History

```python
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("user", "{question}")
])

messages = template.format_messages(
    history=[("user", "Hi"), ("assistant", "Hello!")],
    question="How are you?"
)
```

## Template Composition

### Combining Templates

```python
from langchain.prompts import PromptTemplate

intro = PromptTemplate.from_template("You are a {role}.")
task = PromptTemplate.from_template("Your task is to {task}.")

combined = intro + "\n" + task

prompt = combined.format(role="teacher", task="explain concepts")
```

### Nested Templates

```python
from langchain.prompts import PromptTemplate

system_template = PromptTemplate.from_template(
    "You are a {profession} with {experience} years of experience."
)

user_template = PromptTemplate.from_template(
    "Explain {topic} in simple terms."
)

full_prompt = f"{system_template.format(profession='teacher', experience=10)}\n\n{user_template.format(topic='AI')}"
```

## Few-Shot Prompting

### Using Examples

```python
from langchain.prompts import FewShotPromptTemplate, PromptTemplate

examples = [
    {"input": "happy", "output": "sad"},
    {"input": "tall", "output": "short"},
]

example_template = PromptTemplate(
    input_variables=["input", "output"],
    template="Input: {input}\nOutput: {output}"
)

few_shot_template = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_template,
    prefix="Give the antonym of every input",
    suffix="Input: {adjective}\nOutput:",
    input_variables=["adjective"]
)

prompt = few_shot_template.format(adjective="big")
```

### Dynamic Example Selection

```python
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from langchain.prompts.example_selector import LengthBasedExampleSelector

examples = [
    {"input": "happy", "output": "sad"},
    {"input": "tall", "output": "short"},
    {"input": "energetic", "output": "lethargic"},
]

example_selector = LengthBasedExampleSelector(
    examples=examples,
    example_prompt=PromptTemplate(
        input_variables=["input", "output"],
        template="Input: {input}\nOutput: {output}"
    ),
    max_length=25
)

dynamic_template = FewShotPromptTemplate(
    example_selector=example_selector,
    example_prompt=example_template,
    prefix="Give the antonym of every input",
    suffix="Input: {adjective}\nOutput:",
    input_variables=["adjective"]
)
```

## Template Validation

### Input Validation

```python
from langchain.prompts import PromptTemplate

template = PromptTemplate(
    template="Hello {name}, you are {age} years old.",
    input_variables=["name", "age"],
    validate_template=True
)

try:
    prompt = template.format(name="Alice")
except KeyError as e:
    print(f"Missing variable: {e}")
```

## Output Parsers

### Structured Output

```python
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate

response_schemas = [
    ResponseSchema(name="name", description="The person's name"),
    ResponseSchema(name="age", description="The person's age"),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

format_instructions = output_parser.get_format_instructions()

template = PromptTemplate(
    template="Extract information from: {text}\n\n{format_instructions}",
    input_variables=["text"],
    partial_variables={"format_instructions": format_instructions}
)

prompt = template.format(text="John is 30 years old")
```

## Best Practices

1. **Use Type Hints**: Document expected variable types
2. **Validate Templates**: Enable validation during development
3. **Provide Defaults**: Use partial variables for optional inputs
4. **Keep It Simple**: Avoid overly complex templates
5. **Test Thoroughly**: Test with various inputs

## Common Patterns

### Conditional Templates

```python
from langchain.prompts import PromptTemplate

def get_template(include_examples: bool):
    base = "You are a helpful assistant.\n"
    
    if include_examples:
        base += "\nExamples:\n- Example 1\n- Example 2\n"
    
    base += "\nUser question: {question}"
    
    return PromptTemplate.from_template(base)
```

### Template with Context

```python
from langchain.prompts import PromptTemplate

template = PromptTemplate(
    template="""
Context: {context}

Question: {question}

Instructions:
- Answer based on the context
- Be concise and accurate
- If unsure, say "I don't know"

Answer:
    """,
    input_variables=["context", "question"]
)
```

### Role-Based Templates

```python
from langchain.prompts import ChatPromptTemplate

def create_role_prompt(role: str):
    role_instructions = {
        "teacher": "Explain concepts clearly with examples.",
        "developer": "Provide technical solutions with code.",
        "writer": "Create engaging and creative content."
    }
    
    return ChatPromptTemplate.from_messages([
        ("system", f"You are a {role}. {role_instructions.get(role, '')}"),
        ("user", "{request}")
    ])
```
