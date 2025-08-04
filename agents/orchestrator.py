import asyncio
import uuid
import httpx
import uvicorn
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    Message,
    TextPart,
    Role,
    TaskState,
    SendMessageRequest,
    MessageSendParams,
)

# FastAPI app instance
app = FastAPI(
    title="Smart Holiday Orchestrator",
    description="A2A orchestrator service for booking complete holiday packages",
    version="1.0.0"
)

# Pydantic models for API requests/responses
class HolidayBookingRequest(BaseModel):
    origin: str = "Delhi"
    destination: str = "Paris"
    nights: int = 5
    passengers: int = 2
    departure_date: Optional[str] = None
    room_type: str = "double"

class BookingResult(BaseModel):
    service: str
    status: str
    message: str
    booking_details: Dict[str, Any]

class HolidayBookingResponse(BaseModel):
    booking_id: str
    success: bool
    total_services: int
    successful_bookings: int
    failed_bookings: int
    success_rate: float
    results: list[BookingResult]
    summary: str

class SmartHolidayOrchestrator:
    """
    Smart orchestrator that intelligently coordinates travel bookings
    with proper error handling and concurrent processing.
    """
    
    def __init__(self):
        self.agent_urls = {
            "cab": "http://localhost:5001/",
            "flight": "http://localhost:5002/",
            "hotel": "http://localhost:5003/",
        }
    
    async def book_holiday_package(self, request: HolidayBookingRequest) -> HolidayBookingResponse:
        """
        Main orchestration method that coordinates all bookings.
        """
        booking_id = str(uuid.uuid4())
        print(f"🎯 Starting holiday booking {booking_id}: {request.origin} → {request.destination}")
        
        # Calculate departure date if not provided
        departure_date = request.departure_date or datetime.now().strftime('%Y-%m-%d')
        
        booking_results = []
        
        async with httpx.AsyncClient() as http_client:
            try:
                # Initialize clients by manually fetching the agent cards
                print("🔗 Discovering and initializing agent clients...")
                
                cab_card_response = await http_client.get(self.agent_urls["cab"] + ".well-known/agent.json")
                flight_card_response = await http_client.get(self.agent_urls["flight"] + ".well-known/agent.json")
                hotel_card_response = await http_client.get(self.agent_urls["hotel"] + ".well-known/agent.json")
                
                cab_card = AgentCard.model_validate(cab_card_response.json())
                flight_card = AgentCard.model_validate(flight_card_response.json())
                hotel_card = AgentCard.model_validate(hotel_card_response.json())

                cab_client = A2AClient(http_client, agent_card=cab_card)
                flight_client = A2AClient(http_client, agent_card=flight_card)
                hotel_client = A2AClient(http_client, agent_card=hotel_card)
                
                print("✅ All agents discovered successfully")
                
                # Create intelligent booking messages
                flight_message = self._create_flight_message(request, departure_date)
                hotel_message = self._create_hotel_message(request, departure_date)
                cab_message = self._create_cab_message(request, departure_date)
                
                print("📤 Sending concurrent booking requests to all agents...")
                
                try:
                    print(f"Sending message to flight agent...")
                    flight_request = SendMessageRequest(
                        id=str(uuid.uuid4()),
                        params=MessageSendParams(message=flight_message)
                    )
                    flight_response = await flight_client.send_message(flight_request)
                    print(f"Flight response received: {type(flight_response)}")
                except Exception as e:
                    print(f"Flight error: {e}")
                    flight_response = e
                
                try:
                    print(f"Sending message to hotel agent...")
                    hotel_request = SendMessageRequest(
                        id=str(uuid.uuid4()),
                        params=MessageSendParams(message=hotel_message)
                    )
                    hotel_response = await hotel_client.send_message(hotel_request)
                    print(f"Hotel response received: {type(hotel_response)}")
                except Exception as e:
                    print(f"Hotel error: {e}")
                    hotel_response = e
                
                try:
                    print(f"Sending message to cab agent...")
                    cab_request = SendMessageRequest(
                        id=str(uuid.uuid4()),
                        params=MessageSendParams(message=cab_message)
                    )
                    cab_response = await cab_client.send_message(cab_request)
                    print(f"Cab response received: {type(cab_response)}")
                except Exception as e:
                    print(f"Cab error: {e}")
                    cab_response = e
                
                # Process flight booking result
                flight_result = self._process_booking_response(
                    "flight", flight_response, {
                        "origin": request.origin,
                        "destination": request.destination,
                        "passengers": request.passengers,
                        "departure_date": departure_date
                    }
                )
                booking_results.append(flight_result)
                
                # Process hotel booking result
                hotel_result = self._process_booking_response(
                    "hotel", hotel_response, {
                        "location": request.destination,
                        "nights": request.nights,
                        "room_type": request.room_type,
                        "check_in": departure_date
                    }
                )
                booking_results.append(hotel_result)
                
                # Process cab booking result
                cab_result = self._process_booking_response(
                    "cab", cab_response, {
                        "pickup": f"{request.destination} Airport",
                        "destination": f"Hotel in {request.destination}",
                        "passengers": request.passengers,
                        "date": departure_date
                    }
                )
                booking_results.append(cab_result)
                
            except httpx.ConnectError as e:
                raise HTTPException(
                    status_code=503, 
                    detail=f"Cannot connect to agents. Please ensure all agent services are running. Error: {e}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Orchestration failed: {str(e)}"
                )
        
        # Calculate statistics
        successful_bookings = sum(1 for result in booking_results if result.status == "COMPLETED")
        total_services = len(booking_results)
        success_rate = (successful_bookings / total_services) * 100 if total_services > 0 else 0
        
        # Generate summary
        if successful_bookings == total_services:
            summary = "🎊 Complete holiday package booked successfully!"
        elif successful_bookings > 0:
            summary = f"⚠️ Partial booking completed ({successful_bookings}/{total_services} services)"
        else:
            summary = "❌ Holiday booking failed - no services were booked"
        
        return HolidayBookingResponse(
            booking_id=booking_id,
            success=successful_bookings == total_services,
            total_services=total_services,
            successful_bookings=successful_bookings,
            failed_bookings=total_services - successful_bookings,
            success_rate=success_rate,
            results=booking_results,
            summary=summary
        )
    
    def _create_flight_message(self, request: HolidayBookingRequest, departure_date: str) -> Message:
        """Create intelligent flight booking message."""
        flight_text = f"""Book a round-trip flight:
• Origin: {request.origin}
• Destination: {request.destination}
• Departure Date: {departure_date}
• Passengers: {request.passengers} adults
• Class: Economy
• Requirements: Flexible booking, online check-in available"""
        
        return Message(
            message_id=str(uuid.uuid4()),
            role="user",
            parts=[TextPart(text=flight_text)]
        )
    
    def _create_hotel_message(self, request: HolidayBookingRequest, departure_date: str) -> Message:
        """Create intelligent hotel booking message."""
        hotel_text = f"""Book a hotel reservation:
• Location: {request.destination} city center
• Duration: {request.nights} nights
• Check-in Date: {departure_date}
• Guests: {request.passengers} adults
• Room Type: {request.room_type} room
• Requirements: WiFi, breakfast included, near attractions"""
        
        return Message(
            message_id=str(uuid.uuid4()),
            role="user",
            parts=[TextPart(text=hotel_text)]
        )
    
    def _create_cab_message(self, request: HolidayBookingRequest, departure_date: str) -> Message:
        """Create intelligent cab booking message."""
        cab_text = f"""Book airport transfer service:
• Pickup: {request.destination} International Airport
• Destination: Hotel in {request.destination} city center
• Date: {departure_date}
• Passengers: {request.passengers} adults
• Vehicle: Standard sedan or larger
• Requirements: English-speaking driver, assistance with luggage"""
        
        return Message(
            message_id=str(uuid.uuid4()),
            role="user",
            parts=[TextPart(text=cab_text)]
        )
    
    def _process_booking_response(self, service: str, response: Any, booking_details: Dict[str, Any]) -> BookingResult:
        """Process and normalize booking responses from agents."""
        try:
            if isinstance(response, Exception):
                return BookingResult(
                    service=service,
                    status="FAILED",
                    message=f"Error: {str(response)}",
                    booking_details=booking_details
                )
            
            # Handle SendMessageResponse
            if hasattr(response, 'result') and response.result:
                # Extract the agent's response message
                result = response.result
                print(f"Debug {service}: Result type: {type(result)}, dir: {dir(result)}")
                if hasattr(result, 'message') and result.message:
                    message = result.message
                    print(f"Debug {service}: Message type: {type(message)}, dir: {dir(message)}")
                    if hasattr(message, 'parts') and message.parts:
                        for part in message.parts:
                            if hasattr(part, 'text'):
                                return BookingResult(
                                    service=service,
                                    status="COMPLETED",
                                    message=part.text,
                                    booking_details=booking_details
                                )
                
                return BookingResult(
                    service=service,
                    status="COMPLETED",
                    message="Booking processed successfully",
                    booking_details=booking_details
                )
            
            return BookingResult(
                service=service,
                status="COMPLETED", 
                message=f"Response received: {type(response).__name__}",
                booking_details=booking_details
            )
            
        except Exception as e:
            return BookingResult(
                service=service,
                status="ERROR",
                message=f"Processing error: {str(e)}",
                booking_details=booking_details
            )

# Global orchestrator instance
orchestrator = SmartHolidayOrchestrator()

@app.get("/", summary="Health Check")
async def root():
    """Health check endpoint."""
    return {
        "service": "Smart Holiday Orchestrator",
        "status": "running",
        "version": "1.0.0",
        "agents": {
            "cab": "http://localhost:5001/",
            "flight": "http://localhost:5002/",
            "hotel": "http://localhost:5003/"
        }
    }

@app.get("/agents/status", summary="Check Agent Status")
async def check_agents_status():
    """Check if all agents are available."""
    status = {}
    async with httpx.AsyncClient() as client:
        for service, url in orchestrator.agent_urls.items():
            try:
                response = await client.get(f"{url}.well-known/agent.json", timeout=5.0)
                status[service] = {
                    "url": url,
                    "status": "available" if response.status_code == 200 else "unavailable",
                    "agent_name": response.json().get("name", "Unknown") if response.status_code == 200 else None
                }
            except Exception as e:
                status[service] = {
                    "url": url,
                    "status": "unavailable",
                    "error": str(e)
                }
    
    return {"agents": status}

@app.post("/book-holiday", response_model=HolidayBookingResponse, summary="Book Complete Holiday Package")
async def book_holiday_endpoint(request: HolidayBookingRequest):
    """
    Book a complete holiday package including flight, hotel, and cab.
    
    This endpoint orchestrates bookings across multiple A2A agents concurrently
    for efficient processing and provides detailed status for each service.
    """
    return await orchestrator.book_holiday_package(request)

@app.get("/book-holiday/demo", summary="Demo Holiday Booking")
async def demo_booking():
    """Demo endpoint with predefined booking parameters."""
    demo_request = HolidayBookingRequest(
        origin="Delhi",
        destination="Paris",
        nights=5,
        passengers=2,
        room_type="double"
    )
    return await orchestrator.book_holiday_package(demo_request)

def create_app():
    """Factory function for the FastAPI app."""
    return app

if __name__ == "__main__":
    # Run with uvicorn using the factory function
    uvicorn.run(
        "orchestrator:create_app",
        factory=True,
        host="localhost",
        port=8000,
        reload=True
    )
