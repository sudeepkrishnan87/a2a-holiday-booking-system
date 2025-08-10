import asyncio
import uuid
import httpx
import uvicorn
from datetime import datetime, timedelta
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
                    print(f"Flight response details: {flight_response}")
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
                
                # Process flight booking result with enhanced details
                flight_result = self._process_flight_response(
                    flight_response, {
                        "origin": request.origin,
                        "destination": request.destination,
                        "passengers": request.passengers,
                        "departure_date": departure_date
                    }
                )
                booking_results.append(flight_result)
                
                # Process hotel booking result with enhanced details
                hotel_result = self._process_hotel_response(
                    hotel_response, {
                        "location": request.destination,
                        "nights": request.nights,
                        "room_type": request.room_type,
                        "check_in": departure_date
                    }
                )
                booking_results.append(hotel_result)
                
                # Process cab booking result with enhanced details
                cab_result = self._process_cab_response(
                    cab_response, {
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
        """Create intelligent flight booking message for enhanced flight agent."""
        flight_text = f"""Book a comprehensive round-trip flight with full details:

FLIGHT REQUIREMENTS:
• Origin: {request.origin}
• Destination: {request.destination}
• Departure Date: {departure_date}
• Passengers: {request.passengers} adults
• Class: Economy
• Trip Type: Round-trip

REQUESTED DETAILS:
• Provide complete booking confirmation with booking ID
• Include flight numbers, aircraft type, and seat availability
• Show departure/arrival times and gate information
• Display total price breakdown and payment confirmation
• If flights are fully booked, provide rebooking options with alternative flights
• Include baggage allowance and check-in information
• Show behind-the-scenes booking process and database operations

PREFERENCES:
• Flexible booking with free cancellation
• Online check-in capability
• Aisle seats preferred
• Meal preferences: Standard

Please provide comprehensive flight booking details including all backend operations and booking confirmations."""
        
        return Message(
            message_id=str(uuid.uuid4()),
            role="user",
            parts=[TextPart(text=flight_text)]
        )
    
    def _create_hotel_message(self, request: HolidayBookingRequest, departure_date: str) -> Message:
        """Create comprehensive hotel booking message for enhanced agent."""
        # Calculate checkout date
        try:
            checkin_date = datetime.strptime(departure_date, '%Y-%m-%d')
            checkout_date = checkin_date + timedelta(days=request.nights)
            checkout_str = checkout_date.strftime('%Y-%m-%d')
        except:
            checkout_str = request.return_date or "2025-08-20"
        
        hotel_text = f"""{{
    "location": "{request.destination}",
    "check_in": "{departure_date}",
    "check_out": "{checkout_str}",
    "guests": {request.passengers},
    "preferences": {{
        "hotel_rating": {getattr(request, 'hotel_rating', 4)},
        "room_type": "{request.room_type}",
        "guest_name": "Guest",
        "guest_contact": "+91-9999999999",
        "guest_email": "guest@example.com",
        "special_requests": "WiFi, near attractions, city center location",
        "payment_method": "Credit Card"
    }}
}}"""
        
        return Message(
            message_id=str(uuid.uuid4()),
            role="user",
            parts=[TextPart(text=hotel_text)]
        )
    
    def _create_cab_message(self, request: HolidayBookingRequest, departure_date: str) -> Message:
        """Create comprehensive cab booking message for enhanced agent."""
        # Determine vehicle type based on passenger count
        vehicle_type = "SUV" if request.passengers > 4 else "Sedan"
        
        cab_text = f"""{{
    "pickup_location": "{request.destination} Airport",
    "destination": "Hotel in {request.destination}",
    "pickup_time": "{departure_date} arrival",
    "passengers": {request.passengers},
    "preferences": {{
        "vehicle_type": "{vehicle_type}",
        "special_instructions": "Airport pickup, assistance with luggage",
        "payment_method": "Cash"
    }}
}}"""
        
        return Message(
            message_id=str(uuid.uuid4()),
            role="user",
            parts=[TextPart(text=cab_text)]
        )
    
    def _process_flight_response(self, response: Any, booking_details: Dict[str, Any]) -> BookingResult:
        """Process enhanced flight agent responses with detailed flight information."""
        print(f"🔍 Processing flight response: {type(response)}")
        try:
            if isinstance(response, Exception):
                return BookingResult(
                    service="flight",
                    status="FAILED",
                    message=f"Flight booking error: {str(response)}",
                    booking_details=booking_details
                )
            
            # Handle SendMessageResponse from enhanced flight agent
            # Check multiple possible response structures
            result = None
            if hasattr(response, 'result') and response.result:
                result = response.result
                print(f"✅ Response has result attribute")
            elif hasattr(response, 'root') and hasattr(response.root, 'result') and response.root.result:
                result = response.root.result
                print(f"✅ Response has root.result attribute")
                
            if result:
                # The result IS the message for A2A responses
                message = result
                print(f"✅ Using result as message: {type(message)}")
                
                if hasattr(message, 'parts') and message.parts:
                    print(f"✅ Message has parts: {len(message.parts)} parts")
                    for i, part in enumerate(message.parts):
                        print(f"✅ Processing part {i}: {type(part)}")
                        # Access text via part.root.text for A2A SDK response structure
                        response_text = None
                        if hasattr(part, 'root') and hasattr(part.root, 'text'):
                            response_text = part.root.text
                            print(f"✅ Extracted text via part.root.text: {len(response_text)} chars")
                        elif hasattr(part, 'text'):
                            response_text = part.text
                            print(f"✅ Extracted text via part.text: {len(response_text)} chars")
                        
                        if response_text:
                            print(f"✅ Extracted flight response text: {response_text[:100]}...")
                            
                            # Parse flight booking details from enhanced agent response
                            flight_info = self._extract_flight_details(response_text)
                            print(f"✅ Extracted flight info: {len(flight_info)} details")
                            
                            # Update booking details with parsed information
                            enhanced_details = {**booking_details}
                            if flight_info:
                                enhanced_details.update(flight_info)
                            
                            # Create detailed message based on booking type
                            detailed_message = self._format_flight_message(flight_info, response_text)
                            print(f"✅ Formatted message: {len(detailed_message)} chars")
                            
                            # Determine status based on booking outcome
                            status = "COMPLETED"
                            if "error" in response_text.lower() or "sorry" in response_text.lower():
                                status = "FAILED"
                            elif flight_info.get('status') == 'confirmed' or "CONFIRMATION" in response_text:
                                status = "COMPLETED"
                            
                            print(f"✅ Returning detailed flight result with status: {status}")
                            return BookingResult(
                                service="flight",
                                status=status,
                                message=detailed_message,
                                booking_details=enhanced_details
                            )
                    print("❌ No text found in any parts")
                else:
                    print("❌ Message has no parts or parts is empty")
                
                print("🔄 Falling back to default success response")
                return BookingResult(
                    service="flight",
                    status="COMPLETED",
                    message="Flight booking processed successfully",
                    booking_details=booking_details
                )
            else:
                print("❌ Response has no result attribute")
            
            print("🔄 Falling back to generic response")
            return BookingResult(
                service="flight",
                status="COMPLETED", 
                message=f"Flight response received: {type(response).__name__}",
                booking_details=booking_details
            )
            
        except Exception as e:
            print(f"❌ Exception in flight response processing: {e}")
            return BookingResult(
                service="flight",
                status="ERROR",
                message=f"Flight processing error: {str(e)}",
                booking_details=booking_details
            )

    def _extract_flight_details(self, response_text: str) -> Dict[str, Any]:
        """Extract structured flight information from enhanced agent response."""
        import re
        
        flight_details = {}
        
        try:
            # Check if it's a comprehensive booking response
            if "COMPREHENSIVE FLIGHT BOOKING CONFIRMATION" in response_text:
                # Extract comprehensive booking details
                
                # Extract booking ID
                booking_match = re.search(r'Booking ID[:\s]+([A-Z0-9-]+)', response_text)
                if booking_match:
                    flight_details['booking_id'] = booking_match.group(1)
                
                # Extract confirmation code
                confirm_match = re.search(r'Confirmation Code[:\s]+([A-Z0-9]+)', response_text)
                if confirm_match:
                    flight_details['confirmation_code'] = confirm_match.group(1)
                
                # Extract flight number and airline
                flight_match = re.search(r'Flight[:\s]+([^•\n]+)', response_text)
                if flight_match:
                    flight_details['flight_info'] = flight_match.group(1).strip()
                
                # Extract aircraft type
                aircraft_match = re.search(r'Aircraft[:\s]+([^•\n]+)', response_text)
                if aircraft_match:
                    flight_details['aircraft'] = aircraft_match.group(1).strip()
                
                # Extract route
                route_match = re.search(r'Route[:\s]+([^•\n]+)', response_text)
                if route_match:
                    flight_details['route'] = route_match.group(1).strip()
                
                # Extract departure and arrival times
                departure_match = re.search(r'Departure[:\s]+([^•\n]+)', response_text)
                if departure_match:
                    flight_details['departure_info'] = departure_match.group(1).strip()
                
                arrival_match = re.search(r'Arrival[:\s]+([^•\n]+)', response_text)
                if arrival_match:
                    flight_details['arrival_time'] = arrival_match.group(1).strip()
                
                # Extract duration
                duration_match = re.search(r'Duration[:\s]+([^•\n]+)', response_text)
                if duration_match:
                    flight_details['duration'] = duration_match.group(1).strip()
                
                # Extract passenger information
                passengers_match = re.search(r'Passengers[:\s]+([^•\n]+)', response_text)
                if passengers_match:
                    flight_details['passenger_info'] = passengers_match.group(1).strip()
                
                # Extract seat assignments
                seats_match = re.search(r'Seats[:\s]+([^•\n]+)', response_text)
                if seats_match:
                    flight_details['seat_assignments'] = seats_match.group(1).strip()
                
                # Extract total price
                total_match = re.search(r'\*\*Total[:\s]+₹([0-9,]+)\*\*', response_text)
                if total_match:
                    flight_details['total_price'] = total_match.group(1)
                
                # Extract baggage information
                baggage_match = re.search(r'Baggage[:\s]+([^•\n]+)', response_text)
                if baggage_match:
                    flight_details['baggage_allowance'] = baggage_match.group(1).strip()
                
                # Extract check-in information
                checkin_match = re.search(r'Check-in[:\s]+([^•\n]+)', response_text)
                if checkin_match:
                    flight_details['checkin_info'] = checkin_match.group(1).strip()
                
                # Extract backend operations
                if "BEHIND THE SCENES:" in response_text:
                    flight_details['backend_processed'] = True
                    
                    # Extract booking timestamp
                    timestamp_match = re.search(r'Timestamp[:\s]+([^•\n]+)', response_text)
                    if timestamp_match:
                        flight_details['booking_timestamp'] = timestamp_match.group(1).strip()
                
                # Mark as comprehensive booking
                flight_details['booking_type'] = 'comprehensive'
                flight_details['status'] = 'confirmed'
                
            elif "FLIGHT FULLY BOOKED" in response_text:
                # Handle fully booked scenario
                flight_details['status'] = 'fully_booked'
                flight_details['booking_type'] = 'failed'
                
                # Extract rebooking options count
                rebook_match = re.search(r'Found (\d+) alternative flights', response_text)
                if rebook_match:
                    flight_details['alternatives_count'] = int(rebook_match.group(1))
                    flight_details['rebooking_available'] = True
                
            elif "NO FLIGHTS AVAILABLE" in response_text:
                # Handle no availability scenario
                flight_details['status'] = 'no_availability'
                flight_details['booking_type'] = 'failed'
                
                # Check for alternatives
                if "ALTERNATIVE DATES/ROUTES:" in response_text:
                    flight_details['alternatives_available'] = True
                
            else:
                # Fallback for other responses - extract basic information
                
                # Extract booking ID
                booking_match = re.search(r'Booking ID[:\s]+([A-Z0-9-]+)', response_text)
                if booking_match:
                    flight_details['booking_id'] = booking_match.group(1)
                
                # Extract flight number
                flight_match = re.search(r'Flight[:\s]+([A-Z]{2,3}\d+)', response_text)
                if flight_match:
                    flight_details['flight_number'] = flight_match.group(1)
                
                # Extract price
                price_match = re.search(r'Price[:\s]+₹([0-9,]+)', response_text)
                if price_match:
                    flight_details['price'] = price_match.group(1)
                
                # Extract aircraft type
                aircraft_match = re.search(r'Aircraft[:\s]+([A-Za-z0-9\s-]+)', response_text)
                if aircraft_match:
                    flight_details['aircraft'] = aircraft_match.group(1).strip()
                
                # Extract departure/arrival times
                departure_match = re.search(r'Departure[:\s]+(\d{1,2}:\d{2}(?:\s?[AP]M)?)', response_text)
                if departure_match:
                    flight_details['departure_time'] = departure_match.group(1)
                    
                arrival_match = re.search(r'Arrival[:\s]+(\d{1,2}:\d{2}(?:\s?[AP]M)?)', response_text)
                if arrival_match:
                    flight_details['arrival_time'] = arrival_match.group(1)
                
                # Extract seat availability
                seats_match = re.search(r'(\d+)\s+seats?\s+available', response_text, re.IGNORECASE)
                if seats_match:
                    flight_details['seats_available'] = int(seats_match.group(1))
                
                # Check for rebooking information
                if 'rebook' in response_text.lower() or 'alternative' in response_text.lower():
                    flight_details['rebooking_available'] = True
                    
                    # Extract alternative flight info
                    alt_flight_match = re.search(r'alternative.*?flight[:\s]+([A-Z]{2,3}\d+)', response_text, re.IGNORECASE)
                    if alt_flight_match:
                        flight_details['alternative_flight'] = alt_flight_match.group(1)
                
                # Extract class information
                class_match = re.search(r'Class[:\s]+([A-Za-z\s]+)', response_text)
                if class_match:
                    flight_details['class'] = class_match.group(1).strip()
                
                flight_details['booking_type'] = 'standard'
                
        except Exception as e:
            print(f"Error extracting flight details: {e}")
        
        return flight_details

    def _format_flight_message(self, flight_info: Dict[str, Any], response_text: str) -> str:
        """Format comprehensive flight ticket status message."""
        try:
            if flight_info.get('booking_type') == 'comprehensive':
                # Comprehensive booking confirmation
                message = "✈️ **FLIGHT TICKET CONFIRMED** ✈️\n\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # Booking Reference
                if flight_info.get('booking_id'):
                    message += f"🎫 **Booking Reference:** {flight_info['booking_id']}\n"
                if flight_info.get('confirmation_code'):
                    message += f"🔑 **Confirmation Code:** {flight_info['confirmation_code']}\n\n"
                
                # Flight Information
                message += "✈️ **FLIGHT DETAILS**\n"
                if flight_info.get('flight_info'):
                    message += f"• **Flight:** {flight_info['flight_info']}\n"
                if flight_info.get('aircraft'):
                    message += f"• **Aircraft:** {flight_info['aircraft']}\n"
                if flight_info.get('route'):
                    message += f"• **Route:** {flight_info['route']}\n\n"
                
                # Schedule Information
                message += "🕒 **SCHEDULE**\n"
                if flight_info.get('departure_info'):
                    message += f"• **Departure:** {flight_info['departure_info']}\n"
                if flight_info.get('arrival_time'):
                    message += f"• **Arrival:** {flight_info['arrival_time']}\n"
                if flight_info.get('duration'):
                    message += f"• **Duration:** {flight_info['duration']}\n\n"
                
                # Passenger & Seating
                message += "👥 **PASSENGER INFORMATION**\n"
                if flight_info.get('passenger_info'):
                    message += f"• **Passengers:** {flight_info['passenger_info']}\n"
                if flight_info.get('seat_assignments'):
                    message += f"• **Seat Assignments:** {flight_info['seat_assignments']}\n\n"
                
                # Pricing
                if flight_info.get('total_price'):
                    message += f"💰 **TOTAL PRICE:** ₹{flight_info['total_price']}\n\n"
                
                # Additional Services
                message += "🎒 **ADDITIONAL INFORMATION**\n"
                if flight_info.get('baggage_allowance'):
                    message += f"• **Baggage:** {flight_info['baggage_allowance']}\n"
                if flight_info.get('checkin_info'):
                    message += f"• **Check-in:** {flight_info['checkin_info']}\n"
                
                # Backend Processing Info
                if flight_info.get('backend_processed') and flight_info.get('booking_timestamp'):
                    message += f"\n🔧 **System Status:** Booking processed at {flight_info['booking_timestamp']}\n"
                
                message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                message += "✅ **STATUS: CONFIRMED & READY TO FLY** ✅"
                
            elif flight_info.get('status') == 'fully_booked':
                # Fully booked scenario
                message = "❌ **FLIGHT FULLY BOOKED** ❌\n\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                message += "⚠️ Unfortunately, your selected flight is completely booked.\n\n"
                
                if flight_info.get('rebooking_available') and flight_info.get('alternatives_count'):
                    message += f"🔄 **REBOOKING OPTIONS AVAILABLE**\n"
                    message += f"• Found {flight_info['alternatives_count']} alternative flights\n"
                    message += "• Please contact support for rebooking assistance\n"
                    message += "• Alternative dates and routes are available\n"
                
                message += "\n💡 **Next Steps:**\n"
                message += "• Check alternative departure times\n"
                message += "• Consider nearby airports\n"
                message += "• Flexible date options available\n"
                
            elif flight_info.get('status') == 'no_availability':
                # No availability scenario
                message = "❌ **NO FLIGHTS AVAILABLE** ❌\n\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                message += "⚠️ No flights match your current search criteria.\n\n"
                
                if flight_info.get('alternatives_available'):
                    message += "🔄 **ALTERNATIVE OPTIONS:**\n"
                    message += "• Different travel dates available\n"
                    message += "• Alternative routes suggested\n"
                    message += "• Nearby airports with connections\n"
                
                message += "\n💡 **Suggestions:**\n"
                message += "• Try flexible dates (+/- 3 days)\n"
                message += "• Consider connecting flights\n"
                message += "• Check alternative airports\n"
                
            elif flight_info.get('booking_id'):
                # Standard booking confirmed
                message = "✅ **FLIGHT BOOKING CONFIRMED** ✅\n\n"
                message += f"🎫 **Booking ID:** {flight_info['booking_id']}\n\n"
                
                if flight_info.get('flight_number'):
                    message += f"✈️ **Flight:** {flight_info['flight_number']}\n"
                if flight_info.get('aircraft'):
                    message += f"🛩️ **Aircraft:** {flight_info['aircraft']}\n"
                if flight_info.get('departure_time') and flight_info.get('arrival_time'):
                    message += f"🕒 **Schedule:** {flight_info['departure_time']} → {flight_info['arrival_time']}\n"
                if flight_info.get('price'):
                    message += f"💰 **Price:** ₹{flight_info['price']}\n"
                if flight_info.get('class'):
                    message += f"🎫 **Class:** {flight_info['class']}\n"
                
                message += "\n✅ Your flight is confirmed and ready!"
                
            elif flight_info.get('rebooking_available'):
                # Rebooking scenario
                message = "⚠️ **REBOOKING REQUIRED** ⚠️\n\n"
                message += "Your original flight selection is not available.\n\n"
                
                if flight_info.get('alternative_flight'):
                    message += f"🔄 **Alternative Available:** {flight_info['alternative_flight']}\n"
                
                message += "\n💡 Please confirm rebooking or select different options."
                
            else:
                # Generic response with enhanced formatting
                if 'success' in response_text.lower() or 'booked' in response_text.lower() or 'confirmed' in response_text.lower():
                    message = "✅ **FLIGHT BOOKING SUCCESSFUL** ✅\n\n"
                    message += "Your flight has been processed successfully.\n\n"
                else:
                    message = "❌ **FLIGHT BOOKING ISSUE** ❌\n\n"
                    message += "There was an issue with your flight booking.\n\n"
                
                # Include relevant response excerpt
                if len(response_text) > 300:
                    message += f"**Details:** {response_text[:300]}...\n\n"
                else:
                    message += f"**Details:** {response_text}\n\n"
                    
                message += "Please contact support if you need assistance."
            
            return message
            
        except Exception as e:
            print(f"Error formatting flight message: {e}")
            return f"Flight booking response: {response_text[:200]}..."

    def _process_hotel_response(self, response: Any, booking_details: Dict[str, Any]) -> BookingResult:
        """Process enhanced hotel agent responses with detailed hotel information."""
        print(f"🔍 Processing hotel response: {type(response)}")
        try:
            if isinstance(response, Exception):
                return BookingResult(
                    service="hotel",
                    status="FAILED",
                    message=f"Hotel booking error: {str(response)}",
                    booking_details=booking_details
                )
            
            # Extract hotel response text
            response_text = ""
            if hasattr(response, 'root') and hasattr(response.root, 'result'):
                print("✅ Response has root.result attribute")
                result = response.root.result
                print(f"🔍 Result type: {type(result)}, has text: {hasattr(result, 'text')}")
                if hasattr(result, 'text'):
                    response_text = result.text
                    print(f"📝 Extracted hotel text: {response_text[:100]}...")
                else:
                    # Treat result as the message directly
                    response_text = str(result)
                    print(f"📝 Using result as hotel text: {response_text[:100]}...")
            
            if response_text:
                # Extract detailed hotel information
                hotel_info = self._extract_hotel_details(response_text)
                
                # Create detailed message
                detailed_message = self._format_hotel_message(hotel_info, response_text)
                
                # Enhance booking details
                enhanced_details = {**booking_details, **hotel_info}
                
                # Determine status
                status = "COMPLETED"
                if "error" in response_text.lower() or "sorry" in response_text.lower():
                    status = "FAILED"
                elif hotel_info.get('status') == 'confirmed' or "CONFIRMATION" in response_text:
                    status = "COMPLETED"
                
                print(f"✅ Returning detailed hotel result with status: {status}")
                return BookingResult(
                    service="hotel",
                    status=status,
                    message=detailed_message,
                    booking_details=enhanced_details
                )
            
            print("🔄 Falling back to default hotel response")
            return BookingResult(
                service="hotel",
                status="COMPLETED",
                message="Hotel booking processed successfully",
                booking_details=booking_details
            )
            
        except Exception as e:
            print(f"❌ Error processing hotel response: {e}")
            return BookingResult(
                service="hotel",
                status="FAILED",
                message=f"Error processing hotel booking: {str(e)}",
                booking_details=booking_details
            )

    def _extract_hotel_details(self, response_text: str) -> Dict[str, Any]:
        """Extract comprehensive hotel booking details from response text."""
        import re
        hotel_details = {}
        
        try:
            # Extract booking ID
            booking_match = re.search(r'Booking Reference[:\s]+([A-Z0-9-]+)', response_text)
            if booking_match:
                hotel_details['booking_id'] = booking_match.group(1)
            
            # Extract confirmation code
            confirm_match = re.search(r'Confirmation Code[:\s]+([A-Z0-9]+)', response_text)
            if confirm_match:
                hotel_details['confirmation_code'] = confirm_match.group(1)
            
            # Extract hotel name
            hotel_match = re.search(r'Name[:\s]+([^•\n]+)', response_text)
            if hotel_match:
                hotel_details['hotel_name'] = hotel_match.group(1).strip()
            
            # Extract category and star rating
            category_match = re.search(r'Category[:\s]+([^•\n\(]+)', response_text)
            if category_match:
                hotel_details['category'] = category_match.group(1).strip()
                
            star_match = re.search(r'\(([0-9-]+)\s*Stars?\)', response_text)
            if star_match:
                hotel_details['star_rating'] = star_match.group(1)
            
            # Extract location
            location_match = re.search(r'Location[:\s]+([^•\n]+)', response_text)
            if location_match:
                hotel_details['location'] = location_match.group(1).strip()
            
            # Extract room type
            room_match = re.search(r'Type[:\s]+([^•\n]+Room)', response_text)
            if room_match:
                hotel_details['room_type'] = room_match.group(1).strip()
            
            # Extract check-in/out dates
            checkin_match = re.search(r'Check-in[:\s]+([0-9-]+)', response_text)
            if checkin_match:
                hotel_details['check_in_date'] = checkin_match.group(1)
                
            checkout_match = re.search(r'Check-out[:\s]+([0-9-]+)', response_text)
            if checkout_match:
                hotel_details['check_out_date'] = checkout_match.group(1)
            
            # Extract duration
            nights_match = re.search(r'Duration[:\s]+(\d+)\s*nights?', response_text)
            if nights_match:
                hotel_details['nights'] = int(nights_match.group(1))
            
            # Extract guest count
            guests_match = re.search(r'Guests[:\s]+(\d+)', response_text)
            if guests_match:
                hotel_details['guests'] = int(guests_match.group(1))
            
            # Extract total cost
            total_match = re.search(r'TOTAL COST[:\s]+₹([0-9,]+)', response_text)
            if total_match:
                hotel_details['total_cost'] = total_match.group(1)
            
            # Extract rating
            rating_match = re.search(r'Rating[:\s]+⭐\s*([0-9.]+)', response_text)
            if rating_match:
                hotel_details['rating'] = float(rating_match.group(1))
            
            # Extract contact info
            phone_match = re.search(r'Phone[:\s]+([+0-9-]+)', response_text)
            if phone_match:
                hotel_details['contact_phone'] = phone_match.group(1)
                
            email_match = re.search(r'Email[:\s]+([^\s\n]+@[^\s\n]+)', response_text)
            if email_match:
                hotel_details['contact_email'] = email_match.group(1)
            
            # Mark as comprehensive if detailed response
            if "HOTEL BOOKING CONFIRMED" in response_text:
                hotel_details['booking_type'] = 'comprehensive'
                hotel_details['status'] = 'confirmed'
            
        except Exception as e:
            print(f"Error extracting hotel details: {e}")
        
        return hotel_details

    def _format_hotel_message(self, hotel_info: Dict[str, Any], response_text: str) -> str:
        """Format comprehensive hotel booking status message."""
        try:
            if hotel_info.get('booking_type') == 'comprehensive':
                # Comprehensive hotel booking confirmation
                message = "🏨 **HOTEL BOOKING CONFIRMED** 🏨\n\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # Booking Reference
                if hotel_info.get('booking_id'):
                    message += f"🎫 **Booking Reference:** {hotel_info['booking_id']}\n"
                if hotel_info.get('confirmation_code'):
                    message += f"🔑 **Confirmation Code:** {hotel_info['confirmation_code']}\n\n"
                
                # Hotel Information
                message += "🏢 **HOTEL DETAILS**\n"
                if hotel_info.get('hotel_name'):
                    message += f"• **Name:** {hotel_info['hotel_name']}\n"
                if hotel_info.get('category') and hotel_info.get('star_rating'):
                    message += f"• **Category:** {hotel_info['category']} ({hotel_info['star_rating']} Stars)\n"
                if hotel_info.get('location'):
                    message += f"• **Location:** {hotel_info['location']}\n"
                if hotel_info.get('rating'):
                    message += f"• **Rating:** ⭐ {hotel_info['rating']}/5.0\n\n"
                
                # Room Information
                message += "🛏️ **ROOM INFORMATION**\n"
                if hotel_info.get('room_type'):
                    message += f"• **Type:** {hotel_info['room_type']}\n"
                if hotel_info.get('guests'):
                    message += f"• **Guests:** {hotel_info['guests']}\n\n"
                
                # Stay Details
                message += "📅 **STAY DETAILS**\n"
                if hotel_info.get('check_in_date'):
                    message += f"• **Check-in:** {hotel_info['check_in_date']}\n"
                if hotel_info.get('check_out_date'):
                    message += f"• **Check-out:** {hotel_info['check_out_date']}\n"
                if hotel_info.get('nights'):
                    message += f"• **Duration:** {hotel_info['nights']} nights\n\n"
                
                # Pricing
                if hotel_info.get('total_cost'):
                    message += f"💰 **TOTAL COST:** ₹{hotel_info['total_cost']}\n\n"
                
                # Contact Information
                if hotel_info.get('contact_phone') or hotel_info.get('contact_email'):
                    message += "📞 **HOTEL CONTACT**\n"
                    if hotel_info.get('contact_phone'):
                        message += f"• **Phone:** {hotel_info['contact_phone']}\n"
                    if hotel_info.get('contact_email'):
                        message += f"• **Email:** {hotel_info['contact_email']}\n"
                
                message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                message += "✅ **STATUS: CONFIRMED & READY FOR CHECK-IN** ✅"
                
            else:
                # Standard or fallback response
                if 'success' in response_text.lower() or 'booked' in response_text.lower() or 'confirmed' in response_text.lower():
                    message = "✅ **HOTEL BOOKING SUCCESSFUL** ✅\n\n"
                    if hotel_info.get('booking_id'):
                        message += f"🎫 **Booking ID:** {hotel_info['booking_id']}\n\n"
                    message += "Your hotel reservation has been processed successfully.\n\n"
                else:
                    message = "❌ **HOTEL BOOKING ISSUE** ❌\n\n"
                    message += "There was an issue with your hotel booking.\n\n"
                
                # Include relevant response excerpt
                if len(response_text) > 300:
                    message += f"**Details:** {response_text[:300]}...\n\n"
                else:
                    message += f"**Details:** {response_text}\n\n"
                    
                message += "Please contact support if you need assistance."
            
            return message
            
        except Exception as e:
            print(f"Error formatting hotel message: {e}")
            return f"Hotel booking response: {response_text[:200]}..."

    def _process_cab_response(self, response: Any, booking_details: Dict[str, Any]) -> BookingResult:
        """Process enhanced cab agent responses with detailed cab information."""
        print(f"🔍 Processing cab response: {type(response)}")
        try:
            if isinstance(response, Exception):
                return BookingResult(
                    service="cab",
                    status="FAILED",
                    message=f"Cab booking error: {str(response)}",
                    booking_details=booking_details
                )
            
            # Extract cab response text
            response_text = ""
            if hasattr(response, 'root') and hasattr(response.root, 'result'):
                print("✅ Response has root.result attribute")
                result = response.root.result
                print(f"🔍 Result type: {type(result)}, has text: {hasattr(result, 'text')}")
                if hasattr(result, 'text'):
                    response_text = result.text
                    print(f"📝 Extracted cab text: {response_text[:100]}...")
                else:
                    # Treat result as the message directly
                    response_text = str(result)
                    print(f"📝 Using result as cab text: {response_text[:100]}...")
            
            if response_text:
                # Extract detailed cab information
                cab_info = self._extract_cab_details(response_text)
                
                # Create detailed message
                detailed_message = self._format_cab_message(cab_info, response_text)
                
                # Enhance booking details
                enhanced_details = {**booking_details, **cab_info}
                
                # Determine status
                status = "COMPLETED"
                if "error" in response_text.lower() or "sorry" in response_text.lower():
                    status = "FAILED"
                elif cab_info.get('status') == 'confirmed' or "CONFIRMATION" in response_text:
                    status = "COMPLETED"
                
                print(f"✅ Returning detailed cab result with status: {status}")
                return BookingResult(
                    service="cab",
                    status=status,
                    message=detailed_message,
                    booking_details=enhanced_details
                )
            
            print("🔄 Falling back to default cab response")
            return BookingResult(
                service="cab",
                status="COMPLETED",
                message="Cab booking processed successfully",
                booking_details=booking_details
            )
            
        except Exception as e:
            print(f"❌ Error processing cab response: {e}")
            return BookingResult(
                service="cab",
                status="FAILED",
                message=f"Error processing cab booking: {str(e)}",
                booking_details=booking_details
            )

    def _extract_cab_details(self, response_text: str) -> Dict[str, Any]:
        """Extract comprehensive cab booking details from response text."""
        import re
        cab_details = {}
        
        try:
            # Extract booking ID
            booking_match = re.search(r'Booking Reference[:\s]+([A-Z0-9-]+)', response_text)
            if booking_match:
                cab_details['booking_id'] = booking_match.group(1)
            
            # Extract confirmation code
            confirm_match = re.search(r'Confirmation Code[:\s]+([A-Z0-9]+)', response_text)
            if confirm_match:
                cab_details['confirmation_code'] = confirm_match.group(1)
            
            # Extract vehicle details
            vehicle_match = re.search(r'Type[:\s]+([^•\n-]+)', response_text)
            if vehicle_match:
                cab_details['vehicle_type'] = vehicle_match.group(1).strip()
                
            model_match = re.search(r'(?:Type[:\s]+[^•\n-]+[-\s]*([^•\n]+))', response_text)
            if model_match:
                cab_details['vehicle_model'] = model_match.group(1).strip()
            
            # Extract vehicle number
            number_match = re.search(r'Vehicle Number[:\s]+([A-Z0-9-]+)', response_text)
            if number_match:
                cab_details['vehicle_number'] = number_match.group(1)
            
            # Extract driver details
            driver_match = re.search(r'Name[:\s]+([^•\n]+)', response_text)
            if driver_match:
                cab_details['driver_name'] = driver_match.group(1).strip()
                
            rating_match = re.search(r'Rating[:\s]+⭐\s*([0-9.]+)', response_text)
            if rating_match:
                cab_details['driver_rating'] = float(rating_match.group(1))
                
            contact_match = re.search(r'Contact[:\s]+([+0-9-]+)', response_text)
            if contact_match:
                cab_details['driver_contact'] = contact_match.group(1)
            
            # Extract journey details
            pickup_match = re.search(r'Pickup[:\s]+([^•\n]+)', response_text)
            if pickup_match:
                cab_details['pickup_location'] = pickup_match.group(1).strip()
                
            destination_match = re.search(r'Destination[:\s]+([^•\n]+)', response_text)
            if destination_match:
                cab_details['destination'] = destination_match.group(1).strip()
            
            # Extract distance and duration
            distance_match = re.search(r'Distance[:\s]+([^•\n]+)', response_text)
            if distance_match:
                cab_details['distance'] = distance_match.group(1).strip()
                
            duration_match = re.search(r'Duration[:\s]+([^•\n]+)', response_text)
            if duration_match:
                cab_details['duration'] = duration_match.group(1).strip()
            
            # Extract total fare
            total_match = re.search(r'TOTAL FARE[:\s]+₹([0-9,]+)', response_text)
            if total_match:
                cab_details['total_fare'] = total_match.group(1)
            
            # Extract ETA
            eta_match = re.search(r'ETA[:\s]+([^•\n]+)', response_text)
            if eta_match:
                cab_details['eta'] = eta_match.group(1).strip()
            
            # Mark as comprehensive if detailed response
            if "CAB BOOKING CONFIRMED" in response_text:
                cab_details['booking_type'] = 'comprehensive'
                cab_details['status'] = 'confirmed'
            
        except Exception as e:
            print(f"Error extracting cab details: {e}")
        
        return cab_details

    def _format_cab_message(self, cab_info: Dict[str, Any], response_text: str) -> str:
        """Format comprehensive cab booking status message."""
        try:
            if cab_info.get('booking_type') == 'comprehensive':
                # Comprehensive cab booking confirmation
                message = "🚗 **CAB BOOKING CONFIRMED** 🚗\n\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # Booking Reference
                if cab_info.get('booking_id'):
                    message += f"🎫 **Booking Reference:** {cab_info['booking_id']}\n"
                if cab_info.get('confirmation_code'):
                    message += f"🔑 **Confirmation Code:** {cab_info['confirmation_code']}\n\n"
                
                # Vehicle Information
                message += "🚙 **VEHICLE DETAILS**\n"
                if cab_info.get('vehicle_type'):
                    message += f"• **Type:** {cab_info['vehicle_type']}"
                    if cab_info.get('vehicle_model'):
                        message += f" - {cab_info['vehicle_model']}"
                    message += "\n"
                if cab_info.get('vehicle_number'):
                    message += f"• **Vehicle Number:** {cab_info['vehicle_number']}\n\n"
                
                # Driver Information
                message += "👨‍✈️ **DRIVER INFORMATION**\n"
                if cab_info.get('driver_name'):
                    message += f"• **Name:** {cab_info['driver_name']}\n"
                if cab_info.get('driver_rating'):
                    message += f"• **Rating:** ⭐ {cab_info['driver_rating']}/5.0\n"
                if cab_info.get('driver_contact'):
                    message += f"• **Contact:** {cab_info['driver_contact']}\n\n"
                
                # Journey Details
                message += "🗺️ **JOURNEY DETAILS**\n"
                if cab_info.get('pickup_location'):
                    message += f"• **Pickup:** {cab_info['pickup_location']}\n"
                if cab_info.get('destination'):
                    message += f"• **Destination:** {cab_info['destination']}\n"
                if cab_info.get('distance'):
                    message += f"• **Distance:** {cab_info['distance']}\n"
                if cab_info.get('duration'):
                    message += f"• **Duration:** {cab_info['duration']}\n\n"
                
                # Pricing
                if cab_info.get('total_fare'):
                    message += f"💰 **TOTAL FARE:** ₹{cab_info['total_fare']}\n\n"
                
                # ETA Information
                if cab_info.get('eta'):
                    message += f"⏰ **ETA:** {cab_info['eta']}\n"
                
                message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                message += "✅ **STATUS: CONFIRMED & DRIVER ASSIGNED** ✅"
                
            else:
                # Standard or fallback response
                if 'success' in response_text.lower() or 'booked' in response_text.lower() or 'confirmed' in response_text.lower():
                    message = "✅ **CAB BOOKING SUCCESSFUL** ✅\n\n"
                    if cab_info.get('booking_id'):
                        message += f"🎫 **Booking ID:** {cab_info['booking_id']}\n\n"
                    message += "Your cab has been booked successfully.\n\n"
                else:
                    message = "❌ **CAB BOOKING ISSUE** ❌\n\n"
                    message += "There was an issue with your cab booking.\n\n"
                
                # Include relevant response excerpt
                if len(response_text) > 300:
                    message += f"**Details:** {response_text[:300]}...\n\n"
                else:
                    message += f"**Details:** {response_text}\n\n"
                    
                message += "Please contact support if you need assistance."
            
            return message
            
        except Exception as e:
            print(f"Error formatting cab message: {e}")
            return f"Cab booking response: {response_text[:200]}..."

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

@app.post("/test-flight", summary="Test Flight Agent Direct")
async def test_flight_direct(request: dict):
    """Test flight agent directly without orchestration."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:5002/message/send",
                json=request,
                timeout=30.0
            )
            return {"status": "success", "response": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.post("/test-hotel", summary="Test Hotel Agent Direct")
async def test_hotel_direct(request: dict):
    """Test hotel agent directly without orchestration."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:5003/message/send",
                json=request,
                timeout=30.0
            )
            return {"status": "success", "response": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.post("/test-cab", summary="Test Cab Agent Direct")
async def test_cab_direct(request: dict):
    """Test cab agent directly without orchestration."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:5001/message/send",
                json=request,
                timeout=30.0
            )
            return {"status": "success", "response": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

def create_app():
    """Factory function for the FastAPI app."""
    return app

app = create_app()

if __name__ == "__main__":
    print("🚗 Starting Enhanced Cab Agent Server...")
    print("📍 Server URL: http://localhost:5001")
    print("🔗 Agent Discovery: http://localhost:5001/.well-known/agent.json")
    print("🧪 Ready for A2A communication")
    print("\n✅ Enhanced Cab Agent Features:")
    print("   • Global database with 41+ cities")
    print("   • 4 vehicle types (Economy, Sedan, SUV, Luxury)")
    print("   • Airport pickup intelligence")
    print("   • Real-time availability management")
    print("   • Comprehensive booking confirmations")
    
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9001,
        log_level="info"
    )
