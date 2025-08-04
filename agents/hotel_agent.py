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