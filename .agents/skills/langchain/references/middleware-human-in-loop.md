---
name: middleware-human-in-loop
description: Add human intervention and approval to LangChain agents
---

# Human-in-the-Loop Middleware

> Human-in-the-loop (HITL) allows humans to review, approve, or modify agent actions before execution, ensuring safety and control.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/middleware/built-in#human-in-the-loop

## Basic Usage

### Using Built-in Middleware

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-4",
    tools=[send_email, delete_file, create_user],
    middleware=[HumanInTheLoopMiddleware(
        require_approval_for=["send_email", "delete_file"]
    )]
)
```

### Interactive Approval

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-4",
    tools=[send_email, delete_file],
    middleware=[HumanInTheLoopMiddleware(
        require_approval_for=["send_email", "delete_file"],
        approval_prompt="Tool {tool_name} will be called with args: {args}\nApprove? (y/n): "
    )]
)
```

## Custom HITL Implementation

### Basic Approval

```python
from langchain.agents.middleware import wrap_tool_call, ToolRequest, ToolResponse

@wrap_tool_call
def approval_middleware(request: ToolRequest, handler) -> ToolResponse:
    """Require human approval for sensitive tools."""
    sensitive_tools = ["delete_file", "send_email", "create_user"]
    
    if request.tool_name in sensitive_tools:
        print(f"\nTool: {request.tool_name}")
        print(f"Arguments: {request.args}")
        
        approval = input("Approve? (y/n): ")
        
        if approval.lower() != 'y':
            return ToolResponse(
                content="Operation cancelled by user",
                tool_call_id=request.tool_call_id
            )
    
    return handler(request)
```

### Selective Approval

```python
@wrap_tool_call
def selective_approval_middleware(request: ToolRequest, handler) -> ToolResponse:
    """Approve based on tool and arguments."""
    if request.tool_name == "delete_file":
        print(f"WARNING: About to delete file: {request.args['path']}")
        approval = input("Are you sure? (yes/no): ")
        
        if approval.lower() != 'yes':
            return ToolResponse(
                content="File deletion cancelled",
                tool_call_id=request.tool_call_id
            )
    
    elif request.tool_name == "send_email":
        print(f"To: {request.args['to']}")
        print(f"Subject: {request.args['subject']}")
        approval = input("Send this email? (y/n): ")
        
        if approval.lower() != 'y':
            return ToolResponse(
                content="Email sending cancelled",
                tool_call_id=request.tool_call_id
            )
    
    return handler(request)
```

## Approval Strategies

### Whitelist Approach

```python
@wrap_tool_call
def whitelist_approval_middleware(request: ToolRequest, handler) -> ToolResponse:
    """Only require approval for non-whitelisted tools."""
    safe_tools = ["search", "get_weather", "calculate"]
    
    if request.tool_name not in safe_tools:
        approval = input(f"Approve {request.tool_name}? (y/n): ")
        if approval.lower() != 'y':
            return ToolResponse(
                content="Operation cancelled",
                tool_call_id=request.tool_call_id
            )
    
    return handler(request)
```

### Risk-Based Approval

```python
@wrap_tool_call
def risk_based_approval_middleware(request: ToolRequest, handler) -> ToolResponse:
    """Require approval based on risk level."""
    risk_levels = {
        "delete_file": "high",
        "send_email": "medium",
        "search": "low",
        "get_weather": "low"
    }
    
    risk = risk_levels.get(request.tool_name, "medium")
    
    if risk == "high":
        print(f"HIGH RISK: {request.tool_name}")
        approval = input("Type 'CONFIRM' to proceed: ")
        if approval != 'CONFIRM':
            return ToolResponse(
                content="High-risk operation cancelled",
                tool_call_id=request.tool_call_id
            )
    
    elif risk == "medium":
        approval = input(f"Approve {request.tool_name}? (y/n): ")
        if approval.lower() != 'y':
            return ToolResponse(
                content="Operation cancelled",
                tool_call_id=request.tool_call_id
            )
    
    return handler(request)
```

## Web Interface Integration

### FastAPI with Approval

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

pending_approvals = {}

class ApprovalRequest(BaseModel):
    approval_id: str
    approved: bool

@app.post("/approve")
async def approve_action(approval: ApprovalRequest):
    if approval.approval_id not in pending_approvals:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    pending_approvals[approval.approval_id]["approved"] = approval.approved
    pending_approvals[approval.approval_id]["event"].set()

@wrap_tool_call
async def web_approval_middleware(request: ToolRequest, handler) -> ToolResponse:
    """Web-based approval system."""
    import uuid
    import asyncio
    
    approval_id = str(uuid.uuid4())
    event = asyncio.Event()
    
    pending_approvals[approval_id] = {
        "tool": request.tool_name,
        "args": request.args,
        "approved": False,
        "event": event
    }
    
    print(f"Approval required: {approval_id}")
    print(f"Visit /approve to review")
    
    await event.wait()
    
    if not pending_approvals[approval_id]["approved"]:
        return ToolResponse(
            content="Operation not approved",
            tool_call_id=request.tool_call_id
        )
    
    return handler(request)
```

## Modification Before Execution

### Edit Arguments

```python
@wrap_tool_call
def edit_arguments_middleware(request: ToolRequest, handler) -> ToolResponse:
    """Allow editing tool arguments before execution."""
    print(f"Tool: {request.tool_name}")
    print(f"Current arguments: {request.args}")
    
    edit = input("Edit arguments? (y/n): ")
    
    if edit.lower() == 'y':
        new_args = {}
        for key, value in request.args.items():
            new_value = input(f"{key} [{value}]: ") or value
            new_args[key] = new_value
        
        request = request.override(args=new_args)
    
    return handler(request)
```

### Add Confirmation Details

```python
@wrap_tool_call
def detailed_confirmation_middleware(request: ToolRequest, handler) -> ToolResponse:
    """Show detailed confirmation before execution."""
    if request.tool_name == "send_email":
        print("\n" + "="*50)
        print("EMAIL PREVIEW")
        print("="*50)
        print(f"To: {request.args.get('to')}")
        print(f"Subject: {request.args.get('subject')}")
        print(f"\nBody:\n{request.args.get('body')}")
        print("="*50)
        
        approval = input("\nSend this email? (yes/no): ")
        
        if approval.lower() != 'yes':
            return ToolResponse(
                content="Email cancelled",
                tool_call_id=request.tool_call_id
            )
    
    return handler(request)
```

## Best Practices

1. **Clear Messaging**: Show users exactly what will happen
2. **Easy Cancellation**: Make it simple to cancel operations
3. **Selective Approval**: Don't require approval for safe operations
4. **Timeout Handling**: Implement timeouts for pending approvals
5. **Audit Trail**: Log all approvals and rejections

## Common Patterns

### Timeout-Based Approval

```python
import asyncio

@wrap_tool_call
async def timeout_approval_middleware(request: ToolRequest, handler) -> ToolResponse:
    """Auto-reject after timeout."""
    print(f"Approval required for {request.tool_name}")
    print("You have 30 seconds to respond...")
    
    async def get_approval():
        approval = input("Approve? (y/n): ")
        return approval.lower() == 'y'
    
    try:
        approved = await asyncio.wait_for(get_approval(), timeout=30.0)
    except asyncio.TimeoutError:
        print("\nTimeout - operation cancelled")
        return ToolResponse(
            content="Operation timed out",
            tool_call_id=request.tool_call_id
        )
    
    if not approved:
        return ToolResponse(
            content="Operation cancelled",
            tool_call_id=request.tool_call_id
        )
    
    return handler(request)
```

### Batch Approval

```python
@wrap_model_call
def batch_approval_middleware(request: ModelRequest, handler) -> ModelResponse:
    """Approve multiple tool calls at once."""
    response = handler(request)
    
    if response.tool_calls:
        print(f"\n{len(response.tool_calls)} tool calls pending:")
        for i, call in enumerate(response.tool_calls, 1):
            print(f"{i}. {call['name']}: {call['args']}")
        
        approval = input("\nApprove all? (y/n): ")
        
        if approval.lower() != 'y':
            response.tool_calls = []
            response.content = "Tool calls cancelled by user"
    
    return response
```
