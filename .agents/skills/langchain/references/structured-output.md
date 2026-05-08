---
name: structured-output
description: LangChain structured output for reliable data extraction from LLMs
---

# Structured Output

> Structured output ensures LLMs return data in a specific format, enabling reliable data extraction and type-safe applications.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/structured-output

## Basic Usage

### With Pydantic Model

```python
from pydantic import BaseModel
from langchain.agents import create_agent

class Person(BaseModel):
    name: str
    age: int
    occupation: str

agent = create_agent(
    model="gpt-4",
    output_schema=Person
)

result = agent.invoke({"messages": [{"role": "user", "content": "Extract: John is 30 years old and works as a doctor"}]})

person = result.structured_output
print(person.name)
print(person.age)
print(person.occupation)
```

### With Model Instance

```python
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

class Person(BaseModel):
    name: str
    age: int
    occupation: str

model = ChatOpenAI(model="gpt-4")
structured_model = model.with_structured_output(Person)

result = structured_model.invoke("John is 30 years old and works as a doctor")
print(result.name)
```

## Pydantic Models

### Simple Model

```python
from pydantic import BaseModel

class WeatherReport(BaseModel):
    city: str
    temperature: float
    condition: str
```

### Nested Models

```python
from pydantic import BaseModel

class Address(BaseModel):
    street: str
    city: str
    country: str

class Person(BaseModel):
    name: str
    age: int
    address: Address
```

### Optional Fields

```python
from pydantic import BaseModel, Field
from typing import Optional

class Product(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
```

### Field Descriptions

```python
from pydantic import BaseModel, Field

class Book(BaseModel):
    title: str = Field(description="The title of the book")
    author: str = Field(description="The author's name")
    year: int = Field(description="Publication year")
    rating: float = Field(description="Rating from 0 to 5", ge=0, le=5)
```

## Validation

### Automatic Validation

```python
from pydantic import BaseModel, Field, validator

class Person(BaseModel):
    name: str
    age: int = Field(ge=0, le=150)
    email: str
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
```

### Handling Validation Errors

```python
from pydantic import ValidationError

try:
    person = Person(name="John", age=200, email="invalid")
except ValidationError as e:
    print(f"Validation error: {e}")
```

## JSON Schema

### Automatic Schema Generation

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int

schema = Person.model_json_schema()
print(schema)
```

### Custom Schema

```python
from pydantic import BaseModel, Field

class Person(BaseModel):
    name: str = Field(
        ...,
        description="Person's full name",
        examples=["John Doe"]
    )
    age: int = Field(
        ...,
        description="Person's age",
        ge=0,
        le=150
    )
```

## Common Patterns

### List Extraction

```python
from pydantic import BaseModel
from typing import List

class Person(BaseModel):
    name: str
    age: int

class PeopleList(BaseModel):
    people: List[Person]

agent = create_agent(model="gpt-4", output_schema=PeopleList)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Extract: John (30), Alice (25), Bob (35)"
    }]
})

for person in result.structured_output.people:
    print(f"{person.name}: {person.age}")
```

### Union Types

```python
from pydantic import BaseModel
from typing import Union, Literal

class TextContent(BaseModel):
    type: Literal["text"]
    content: str

class ImageContent(BaseModel):
    type: Literal["image"]
    url: str
    alt_text: str

class Content(BaseModel):
    data: Union[TextContent, ImageContent]
```

### Enum Values

```python
from pydantic import BaseModel
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task(BaseModel):
    title: str
    priority: Priority
```

## Error Handling

### Retry on Parse Error

```python
from langchain.agents import create_agent
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int

agent = create_agent(model="gpt-4", output_schema=Person, max_retries=3)

try:
    result = agent.invoke({"messages": [...]})
    person = result.structured_output
except Exception as e:
    print(f"Failed to extract structured data: {e}")
```

### Fallback to Raw Output

```python
from pydantic import BaseModel
import json

class Person(BaseModel):
    name: str
    age: int

agent = create_agent(model="gpt-4", output_schema=Person)

result = agent.invoke({"messages": [...]})

if result.structured_output:
    person = result.structured_output
else:
    try:
        person = Person.model_validate_json(result.content)
    except:
        person = None
```

## Best Practices

1. **Use Field Descriptions**: Help the LLM understand each field
2. **Set Constraints**: Use validators and Field constraints
3. **Handle Errors**: Always wrap in try-except
4. **Provide Examples**: Use Field(examples=[...]) for clarity
5. **Test Thoroughly**: Validate with various inputs

## Advanced Usage

### Dynamic Schema

```python
from pydantic import BaseModel, create_model

def create_person_model(fields: dict):
    return create_model('DynamicPerson', **fields)

PersonModel = create_person_model({
    'name': (str, ...),
    'age': (int, ...),
    'email': (str, None)
})

agent = create_agent(model="gpt-4", output_schema=PersonModel)
```

### Multi-Step Extraction

```python
from pydantic import BaseModel

class Entity(BaseModel):
    name: str
    type: str

class Relationship(BaseModel):
    source: str
    target: str
    relation: str

agent = create_agent(model="gpt-4")

result1 = agent.invoke({
    "messages": [{"role": "user", "content": "Extract entities from: John works at Google"}],
    "output_schema": Entity
})

result2 = agent.invoke({
    "messages": [{"role": "user", "content": "Extract relationships"}],
    "output_schema": Relationship
})
```
