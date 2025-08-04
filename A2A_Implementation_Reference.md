# A2A (Agent-to-Agent) Implementation Reference

## Project Overview
This project implements an A2A (Agent-to-Agent) communication system using Python, Flask, and the A2A SDK. The system consists of multiple specialized agents (Flight, Hotel, Cab) that can communicate with each other to handle travel booking requests, plus an orchestrator client that coordinates the booking process.

## Project Structure
```
A2A/
├── app.py                          # Main Flask application (legacy)
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── A2A_Implementation_Reference.md # This reference document
├── .venv/                         # Virtual environment
├── .vscode/
│   └── tasks.json                 # VS Code tasks configuration
└── agents/
    ├── __init__.py
    ├── cab_agent.py               # Cab booking agent (A2A SDK implementation)
    ├── flight_agent.py            # Flight booking agent (A2A SDK implementation)
    ├── hotel_agent.py             # Hotel booking agent (A2A SDK implementation)
    └── orchastrator.py            # Client orchestrator for testing
```

## Dependencies (requirements.txt)
```
Flask==3.0.3
requests==2.32.3
a2a-sdk==0.3.0
uvicorn==0.30.6
typing-extensions==4.12.2
```

## Virtual Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

## A2A SDK Implementation Pattern

### Complete Working Cab Agent (cab_agent.py)
```python
import uuid
import uvicorn
from typing_extensions import override
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, Task, TextPart, TaskStatus, TaskState, Message

class CabBookingExecutor(AgentExecutor):
    """
    This class contains the actual logic for the agent.
    It implements the `execute` method to handle incoming tasks.
    """
    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        # We simulate the task process with an immediate response.
        user_message_text = context.task.messages[0].parts[0].text
        print(f"Cab agent received request: {user_message_text}")
        
        # Simulate a booking confirmation
        booking_details = "Cab booking confirmed for your holiday."
        
        response_message = Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[TextPart(text=booking_details)],
        )

        # Enqueue the response message and update the task status to COMPLETED
        await event_queue.put(response_message)
        await event_queue.put(TaskStatus(state=TaskState.COMPLETED))
    
    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Handle task cancellation
        print(f"Cancelling task: {context.task.id}")
        await event_queue.put(TaskStatus(state=TaskState.CANCELLED))

def create_app():
    """
    Factory function to create the A2A application.
    This is a common pattern for ASGI apps.
    """
    agent_card = AgentCard(
        name="CabBookingAgent",
        description="An agent for booking cabs.",
        url="http://localhost:5001/",
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="book-cab",
                name="Book a Cab",
                description="Books a cab from a given location to a destination.",
                input_modes=["text"],
                output_modes=["text"],
                tags=[],  # Required field
            )
        ],
        defaultInputModes=["text"],      # Required field
        defaultOutputModes=["text"],     # Required field
    )
    
    request_handler = DefaultRequestHandler(
        agent_executor=CabBookingExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    # Build and return the Starlette app - IMPORTANT: Must call .build()
    return a2a_app.build()

if __name__ == "__main__":
    # Use uvicorn.run() to start the server.
    uvicorn.run(
        "cab_agent:create_app", 
        host="localhost", 
        port=5001,
        factory=True  # Required for factory function
    )
```

### Complete Working Flight Agent (flight_agent.py)
```python
import uuid
import uvicorn
from typing_extensions import override
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, Task, TextPart, TaskStatus, TaskState, Message

class FlightBookingExecutor(AgentExecutor):
    """
    This class contains the actual logic for the flight booking agent.
    It implements the `execute` method to handle incoming tasks.
    """
    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        # We simulate the flight booking process with an immediate response.
        user_message_text = context.task.messages[0].parts[0].text
        print(f"Flight agent received request: {user_message_text}")
        
        # Simulate a flight booking confirmation
        booking_details = "Flight booking confirmed for your holiday."
        
        response_message = Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[TextPart(text=booking_details)],
        )

        # Enqueue the response message and update the task status to COMPLETED
        await event_queue.put(response_message)
        await event_queue.put(TaskStatus(state=TaskState.COMPLETED))
    
    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Handle task cancellation
        print(f"Cancelling flight booking task: {context.task.id}")
        await event_queue.put(TaskStatus(state=TaskState.CANCELLED))

def create_app():
    """
    Factory function to create the A2A application.
    This is a common pattern for ASGI apps.
    """
    agent_card = AgentCard(
        name="FlightBookingAgent",
        description="An agent for booking flights.",
        url="http://localhost:5002/",
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="book-flight",
                name="Book a Flight",
                description="Books a flight from a given origin to a destination.",
                input_modes=["text"],
                output_modes=["text"],
                tags=[],
            )
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
    )
    
    request_handler = DefaultRequestHandler(
        agent_executor=FlightBookingExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    # Build and return the Starlette app
    return a2a_app.build()

if __name__ == "__main__":
    # Use uvicorn.run() to start the server.
    uvicorn.run(
        "flight_agent:create_app", 
        host="localhost", 
        port=5002,
        factory=True
    )
```

### Complete Working Hotel Agent (hotel_agent.py)
```python
import uuid
import uvicorn
from typing_extensions import override
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, Task, TextPart, TaskStatus, TaskState, Message

class HotelBookingExecutor(AgentExecutor):
    """
    This class contains the actual logic for the hotel booking agent.
    It implements the `execute` method to handle incoming tasks.
    """
    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        # We simulate the hotel booking process with an immediate response.
        user_message_text = context.task.messages[0].parts[0].text
        print(f"Hotel agent received request: {user_message_text}")
        
        # Simulate a hotel booking confirmation
        booking_details = "Hotel booking confirmed for your holiday."
        
        response_message = Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[TextPart(text=booking_details)],
        )

        # Enqueue the response message and update the task status to COMPLETED
        await event_queue.put(response_message)
        await event_queue.put(TaskStatus(state=TaskState.COMPLETED))
    
    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Handle task cancellation
        print(f"Cancelling hotel booking task: {context.task.id}")
        await event_queue.put(TaskStatus(state=TaskState.CANCELLED))

def create_app():
    """
    Factory function to create the A2A application.
    This is a common pattern for ASGI apps.
    """
    agent_card = AgentCard(
        name="HotelBookingAgent",
        description="An agent for booking hotels.",
        url="http://localhost:5003/",
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="book-hotel",
                name="Book a Hotel",
                description="Books a hotel in a specific city.",
                input_modes=["text"],
                output_modes=["text"],
                tags=[],
            )
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
    )
    
    request_handler = DefaultRequestHandler(
        agent_executor=HotelBookingExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    # Build and return the Starlette app
    return a2a_app.build()

if __name__ == "__main__":
    # Use uvicorn.run() to start the server.
    uvicorn.run(
        "hotel_agent:create_app", 
        host="localhost", 
        port=5003,
        factory=True
    )
```

### Complete Orchestrator Client (orchastrator.py)
```python
import asyncio
import uuid
from a2a.client import A2AClient
from a2a.types import (
    Message,
    TextPart,
    SendTaskRequest,
    TaskStatus,
    TaskState
)

async def book_holiday():
    print("Holiday booking client is starting...")

    # Initialize clients for each agent
    cab_client = A2AClient("http://localhost:5001/")
    flight_client = A2AClient("http://localhost:5002/")
    hotel_client = A2AClient("http://localhost:5003/")
    
    print("Agents discovered and clients initialized.")
    
    # Define the booking requests
    flight_request = Message(
        message_id=str(uuid.uuid4()),
        role="user",
        parts=[TextPart(text="Book a round-trip flight from Delhi to Paris.")]
    )
    
    hotel_request = Message(
        message_id=str(uuid.uuid4()),
        role="user",
        parts=[TextPart(text="Book a hotel for 5 nights in Paris.")]
    )
    
    cab_request = Message(
        message_id=str(uuid.uuid4()),
        role="user",
        parts=[TextPart(text="Book a cab from Paris airport to the hotel.")]
    )
    
    # Send tasks to each agent concurrently
    print("Sending booking requests to the agents...")
    
    # Note: In a real-world app, you'd chain these or use a manager agent.
    # Here we'll send them all at once for simplicity.
    flight_task_request = SendTaskRequest(task_id=str(uuid.uuid4()), message=flight_request)
    hotel_task_request = SendTaskRequest(task_id=str(uuid.uuid4()), message=hotel_request)
    cab_task_request = SendTaskRequest(task_id=str(uuid.uuid4()), message=cab_request)
    
    try:
        flight_task_response = await flight_client.send_task(flight_task_request)
        hotel_task_response = await hotel_client.send_task(hotel_task_request)
        cab_task_response = await cab_client.send_task(cab_task_request)

        print("\n--- Booking Results ---")
        
        # Process flight booking response
        flight_status = flight_task_response.task.status.state
        flight_message = flight_task_response.task.messages[-1].parts[0].text
        print(f"Flight Booking Status: {flight_status.value}")
        print(f"  > Message: {flight_message}")

        # Process hotel booking response
        hotel_status = hotel_task_response.task.status.state
        hotel_message = hotel_task_response.task.messages[-1].parts[0].text
        print(f"Hotel Booking Status: {hotel_status.value}")
        print(f"  > Message: {hotel_message}")

        # Process cab booking response
        cab_status = cab_task_response.task.status.state
        cab_message = cab_task_response.task.messages[-1].parts[0].text
        print(f"Cab Booking Status: {cab_status.value}")
        print(f"  > Message: {cab_message}")
        
        print("\nHoliday booking process completed.")

    except Exception as e:
        print(f"An error occurred during booking: {e}")

if __name__ == "__main__":
    asyncio.run(book_holiday())
```

## Key A2A SDK Concepts

### 1. AgentExecutor
- Must inherit from `AgentExecutor`
- **Required methods:**
  - `execute(context, event_queue)` - Main task processing logic
  - `cancel(context, event_queue)` - Handle task cancellation
- Use `@override` decorator for methods

### 2. AgentCard
- Metadata describing the agent's capabilities
- **Required fields:**
  - `name`, `description`, `url`, `version`
  - `capabilities`, `skills`
  - `defaultInputModes`, `defaultOutputModes`

### 3. AgentSkill
- Describes what the agent can do
- **Required fields:**
  - `id`, `name`, `description`
  - `input_modes`, `output_modes`
  - `tags` (can be empty list)

### 4. A2AStarletteApplication
- Main application wrapper
- **Must call `.build()`** to get the actual ASGI app
- Use with uvicorn factory pattern

### 5. A2AClient
- Client for sending tasks to agents
- Initialize with agent URL
- Use `send_task()` method for task requests

## Server Startup Patterns

### Method 1: Factory Function (Recommended)
```python
def create_app():
    # ... setup code ...
    return a2a_app.build()

if __name__ == "__main__":
    uvicorn.run(
        "module_name:create_app", 
        host="localhost", 
        port=5001,
        factory=True
    )
```

### Method 2: Direct Run (Alternative)
```python
async def main():
    # ... setup code ...
    config = uvicorn.Config(a2a_app.build(), host="localhost", port=5001)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Complete System Operation

### Starting All Agents
```bash
# Terminal 1: Start Cab Agent
source .venv/bin/activate
python agents/cab_agent.py

# Terminal 2: Start Flight Agent  
source .venv/bin/activate
python agents/flight_agent.py

# Terminal 3: Start Hotel Agent
source .venv/bin/activate
python agents/hotel_agent.py

# Terminal 4: Run Orchestrator
source .venv/bin/activate
python agents/orchastrator.py
```

### Expected Orchestrator Output
```
Holiday booking client is starting...
Agents discovered and clients initialized.
Sending booking requests to the agents...

--- Booking Results ---
Flight Booking Status: COMPLETED
  > Message: Flight booking confirmed for your holiday.
Hotel Booking Status: COMPLETED
  > Message: Hotel booking confirmed for your holiday.
Cab Booking Status: COMPLETED
  > Message: Cab booking confirmed for your holiday.

Holiday booking process completed.
```

## Testing and Validation

### Agent Discovery Endpoints
```bash
# Test Cab Agent
curl http://localhost:5001/.well-known/agent.json

# Test Flight Agent
curl http://localhost:5002/.well-known/agent.json

# Test Hotel Agent
curl http://localhost:5003/.well-known/agent.json
```

### Expected Discovery Response Format
```json
{
  "capabilities": {},
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "description": "An agent for booking [service].",
  "name": "[Service]BookingAgent",
  "preferredTransport": "JSONRPC",
  "protocolVersion": "0.3.0",
  "skills": [{
    "description": "Books a [service] [specific description].",
    "id": "book-[service]",
    "inputModes": ["text"],
    "name": "Book a [Service]",
    "outputModes": ["text"],
    "tags": []
  }],
  "url": "http://localhost:[port]/",
  "version": "1.0.0"
}
```

### Testing Individual Agents
```bash
# Test all agent discovery endpoints at once
echo "Testing all agent discovery endpoints:" && \
echo "Cab Agent:" && curl -s http://localhost:5001/.well-known/agent.json | grep -o '"name":"[^"]*"' && \
echo "" && echo "Flight Agent:" && curl -s http://localhost:5002/.well-known/agent.json | grep -o '"name":"[^"]*"' && \
echo "" && echo "Hotel Agent:" && curl -s http://localhost:5003/.well-known/agent.json | grep -o '"name":"[^"]*"'
```

## Common Issues and Solutions

### 1. ImportError: No module named 'a2a.sdk'
**Problem:** Wrong import path
**Solution:** Use `from a2a.server import ...` not `from a2a.sdk.server import ...`

### 2. ValidationError: Field required
**Problem:** Missing required fields in AgentCard or AgentSkill
**Solution:** Ensure all required fields are present:
- AgentSkill: add `tags=[]`
- AgentCard: add `defaultInputModes=["text"]`, `defaultOutputModes=["text"]`

### 3. TypeError: 'A2AStarletteApplication' object is not callable
**Problem:** Not calling `.build()` on A2AStarletteApplication
**Solution:** Always call `a2a_app.build()` before passing to uvicorn

### 4. Can't instantiate abstract class without implementation for abstract method 'cancel'
**Problem:** Missing cancel method in AgentExecutor
**Solution:** Implement the `cancel` method with `@override` decorator

### 5. Address already in use
**Problem:** Port conflict with existing process
**Solution:** Kill existing process or use different port:
```bash
pkill -f "python.*agent_name.py"
# or change port number
```

### 6. Connection refused in orchestrator
**Problem:** Agents not running or wrong URLs
**Solution:** Ensure all agents are running on correct ports:
```bash
# Check what's running on ports
lsof -i :5001
lsof -i :5002  
lsof -i :5003
```

## A2A Package Structure
```
a2a/
├── server/
│   ├── apps.py                 # A2AStarletteApplication
│   ├── request_handlers.py     # DefaultRequestHandler
│   ├── tasks.py               # InMemoryTaskStore
│   ├── agent_execution.py     # AgentExecutor, RequestContext
│   └── events.py              # EventQueue
├── client.py                  # A2AClient for orchestration
├── types.py                   # AgentCard, AgentSkill, Message, etc.
├── auth.py                    # Authentication
└── utils.py                   # Utility functions
```

## Port Assignments and Status
| Agent | Port | Status | Framework | Endpoint |
|-------|------|--------|-----------|----------|
| Cab | 5001 | ✅ Working | A2A SDK | http://localhost:5001 |
| Flight | 5002 | ✅ Working | A2A SDK | http://localhost:5002 |
| Hotel | 5003 | ✅ Working | A2A SDK | http://localhost:5003 |
| Orchestrator | - | ✅ Working | A2A Client | - |

## Development Workflow

### 1. Development Setup
```bash
# Clone/setup project
cd A2A
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Running Individual Agents
```bash
# Start agents in separate terminals
python agents/cab_agent.py     # Port 5001
python agents/flight_agent.py  # Port 5002  
python agents/hotel_agent.py   # Port 5003
```

### 3. Testing the System
```bash
# Run the orchestrator to test end-to-end flow
python agents/orchastrator.py
```

### 4. Development Tips
- Always activate virtual environment first
- Start agents before running orchestrator
- Check agent discovery endpoints for debugging
- Use `pkill` to stop agents cleanly
- Monitor console output for task processing

## Migration Notes

### From Flask to A2A SDK Pattern
1. **Change imports**: `a2a.sdk.*` → `a2a.server.*` and `a2a.types`
2. **Update class**: `A2AServer` → `AgentExecutor`
3. **Method signatures**: `handle_task(task)` → `execute(context, event_queue)`
4. **Add required method**: `cancel(context, event_queue)`
5. **Use factory pattern**: `create_app()` with `.build()`
6. **Add required fields**: `tags`, `defaultInputModes`, `defaultOutputModes`
7. **Event queue**: Use `event_queue.put()` instead of direct task manipulation

## Next Steps
1. ✅ All agents migrated to A2A SDK
2. ✅ Orchestrator working with all agents
3. 🔄 Add error handling and retry logic
4. 🔄 Implement proper logging
5. 🔄 Add authentication if needed
6. 🔄 Add more sophisticated booking logic
7. 🔄 Add data validation and business rules
8. 🔄 Add persistence layer for bookings

## Useful Commands
```bash
# Environment Management
source .venv/bin/activate                    # Activate virtual environment
deactivate                                  # Deactivate virtual environment
pip list | grep a2a                        # Check A2A SDK installation

# Process Management
lsof -i :5001                              # Check what's running on port 5001
pkill -f "python.*cab_agent.py"            # Kill specific agent
pkill -f "python.*agent"                   # Kill all agents

# Testing
curl http://localhost:5001/.well-known/agent.json  # Test agent discovery
python agents/orchastrator.py                      # Run full system test

# Development
python agents/cab_agent.py                 # Run cab agent
python agents/flight_agent.py              # Run flight agent  
python agents/hotel_agent.py               # Run hotel agent

# Debugging
python -c "import a2a; print(a2a.__version__)"     # Check A2A version
python -c "from a2a.types import AgentCard"        # Test imports
```

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cab Agent     │    │  Flight Agent   │    │  Hotel Agent    │
│   Port: 5001    │    │   Port: 5002    │    │   Port: 5003    │
│                 │    │                 │    │                 │
│ A2AStarlette    │    │ A2AStarlette    │    │ A2AStarlette    │
│ Application     │    │ Application     │    │ Application     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         │              A2A Protocol (JSON-RPC)          │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Orchestrator   │
                    │    (Client)     │
                    │                 │
                    │   A2AClient     │
                    │   Instances     │
                    └─────────────────┘
```

---
*This document captures the complete implementation context for the A2A SDK integration project as of August 4, 2025. All agents successfully migrated and orchestrator working.*
