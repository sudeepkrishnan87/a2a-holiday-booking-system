#!/usr/bin/env python3
"""
🚗 ENHANCED CAB BOOKING AGENT
============================
Comprehensive cab booking service with global database and detailed responses.
Similar architecture to the enhanced flight agent for consistent user experience.

Features:
- Global cab fleet database with 30+ cities
- Multiple vehicle types (Sedan, SUV, Luxury, Electric)
- Dynamic pricing and availability
- Comprehensive booking confirmations
- Real-time fleet management
- Detailed booking responses with driver info, vehicle details, pricing breakdown
"""

import uuid
import uvicorn
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from typing_extensions import override
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, Task, TextPart, TaskStatus, TaskState, Message


class GlobalCabDatabase:
    """Global cab fleet database with comprehensive vehicle and driver information"""
    
    def __init__(self):
        self.cities = {
            # Indian Cities
            "Mumbai": {"timezone": "Asia/Kolkata", "country": "India", "surge_factor": 1.2},
            "Delhi": {"timezone": "Asia/Kolkata", "country": "India", "surge_factor": 1.1},
            "Bangalore": {"timezone": "Asia/Kolkata", "country": "India", "surge_factor": 1.3},
            "Chennai": {"timezone": "Asia/Kolkata", "country": "India", "surge_factor": 1.1},
            "Kolkata": {"timezone": "Asia/Kolkata", "country": "India", "surge_factor": 1.0},
            "Hyderabad": {"timezone": "Asia/Kolkata", "country": "India", "surge_factor": 1.2},
            "Pune": {"timezone": "Asia/Kolkata", "country": "India", "surge_factor": 1.1},
            "Gurgaon": {"timezone": "Asia/Kolkata", "country": "India", "surge_factor": 1.4},
            
            # International Cities
            "New York": {"timezone": "America/New_York", "country": "USA", "surge_factor": 1.5},
            "London": {"timezone": "Europe/London", "country": "UK", "surge_factor": 1.3},
            "Paris": {"timezone": "Europe/Paris", "country": "France", "surge_factor": 1.2},
            "Tokyo": {"timezone": "Asia/Tokyo", "country": "Japan", "surge_factor": 1.6},
            "Singapore": {"timezone": "Asia/Singapore", "country": "Singapore", "surge_factor": 1.4},
            "Dubai": {"timezone": "Asia/Dubai", "country": "UAE", "surge_factor": 1.3},
            "Sydney": {"timezone": "Australia/Sydney", "country": "Australia", "surge_factor": 1.2},
            "San Francisco": {"timezone": "America/Los_Angeles", "country": "USA", "surge_factor": 1.7},
            "Toronto": {"timezone": "America/Toronto", "country": "Canada", "surge_factor": 1.2},
            "Bangkok": {"timezone": "Asia/Bangkok", "country": "Thailand", "surge_factor": 1.1},
            "Hong Kong": {"timezone": "Asia/Hong_Kong", "country": "Hong Kong", "surge_factor": 1.4},
            "Berlin": {"timezone": "Europe/Berlin", "country": "Germany", "surge_factor": 1.1},
            "Amsterdam": {"timezone": "Europe/Amsterdam", "country": "Netherlands", "surge_factor": 1.2},
            "Stockholm": {"timezone": "Europe/Stockholm", "country": "Sweden", "surge_factor": 1.3},
            "Zurich": {"timezone": "Europe/Zurich", "country": "Switzerland", "surge_factor": 1.5},
            "Milan": {"timezone": "Europe/Rome", "country": "Italy", "surge_factor": 1.2},
            "Barcelona": {"timezone": "Europe/Madrid", "country": "Spain", "surge_factor": 1.1},
            "Vienna": {"timezone": "Europe/Vienna", "country": "Austria", "surge_factor": 1.2},
            "Copenhagen": {"timezone": "Europe/Copenhagen", "country": "Denmark", "surge_factor": 1.3},
            "Oslo": {"timezone": "Europe/Oslo", "country": "Norway", "surge_factor": 1.4},
            "Helsinki": {"timezone": "Europe/Helsinki", "country": "Finland", "surge_factor": 1.2},
            "Brussels": {"timezone": "Europe/Brussels", "country": "Belgium", "surge_factor": 1.1},
            "Prague": {"timezone": "Europe/Prague", "country": "Czech Republic", "surge_factor": 1.0},
            "Budapest": {"timezone": "Europe/Budapest", "country": "Hungary", "surge_factor": 0.9},
            "Warsaw": {"timezone": "Europe/Warsaw", "country": "Poland", "surge_factor": 0.8},
            "Moscow": {"timezone": "Europe/Moscow", "country": "Russia", "surge_factor": 1.0},
            "Istanbul": {"timezone": "Europe/Istanbul", "country": "Turkey", "surge_factor": 0.9},
            "Cairo": {"timezone": "Africa/Cairo", "country": "Egypt", "surge_factor": 0.7},
            "Tel Aviv": {"timezone": "Asia/Jerusalem", "country": "Israel", "surge_factor": 1.2},
            "Seoul": {"timezone": "Asia/Seoul", "country": "South Korea", "surge_factor": 1.3},
            "Beijing": {"timezone": "Asia/Shanghai", "country": "China", "surge_factor": 1.1},
            "Shanghai": {"timezone": "Asia/Shanghai", "country": "China", "surge_factor": 1.2},
            "Kuala Lumpur": {"timezone": "Asia/Kuala_Lumpur", "country": "Malaysia", "surge_factor": 1.0}
        }
        
        self.vehicle_types = {
            "Sedan": {
                "base_rate": 12,
                "per_km": 8,
                "capacity": 4,
                "models": ["Toyota Camry", "Honda Accord", "Hyundai Elantra", "Maruti Dzire", "Tata Tigor"],
                "features": ["AC", "GPS", "Music System", "Phone Charger"],
                "description": "Comfortable sedan for city rides"
            },
            "SUV": {
                "base_rate": 18,
                "per_km": 12,
                "capacity": 7,
                "models": ["Toyota Innova", "Mahindra XUV500", "Ford Endeavour", "Hyundai Creta", "Tata Safari"],
                "features": ["AC", "GPS", "Music System", "Phone Charger", "Extra Luggage Space"],
                "description": "Spacious SUV for families and groups"
            },
            "Luxury": {
                "base_rate": 35,
                "per_km": 25,
                "capacity": 4,
                "models": ["Mercedes E-Class", "BMW 5 Series", "Audi A6", "Jaguar XF", "Volvo S90"],
                "features": ["Premium AC", "GPS", "Premium Sound", "WiFi", "Leather Seats", "Chauffeur"],
                "description": "Premium luxury vehicles with professional chauffeurs"
            },
            "Electric": {
                "base_rate": 15,
                "per_km": 10,
                "capacity": 4,
                "models": ["Tesla Model 3", "Tata Nexon EV", "Hyundai Kona Electric", "MG ZS EV", "BMW i3"],
                "features": ["Silent Drive", "Eco-Friendly", "GPS", "AC", "Fast Charging"],
                "description": "Eco-friendly electric vehicles"
            }
        }
        
        self.driver_names = [
            "Rajesh Kumar", "Amit Singh", "Pradeep Sharma", "Suresh Yadav", "Vikash Gupta",
            "Mohammad Ali", "Ravi Verma", "Santosh Jain", "Deepak Tiwari", "Ajay Mehta",
            "John Smith", "Michael Johnson", "David Brown", "James Wilson", "Robert Davis",
            "Wei Chen", "Hiroshi Tanaka", "Ahmed Hassan", "Carlos Rodriguez", "Pierre Martin"
        ]
        
        self.booking_counter = 1000
        
    def search_cabs(self, pickup_location: str, destination: str, pickup_time: str, 
                   passengers: int, preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for available cabs based on criteria"""
        
        # Handle airport locations by extracting city name
        city_name = pickup_location
        if "Airport" in pickup_location:
            city_name = pickup_location.replace(" Airport", "").replace("Airport", "")
        
        if city_name not in self.cities:
            return []
            
        available_cabs = []
        city_info = self.cities[city_name]
        
        # Filter vehicle types based on passenger count
        suitable_types = [vtype for vtype, info in self.vehicle_types.items() 
                         if info["capacity"] >= passengers]
        
        # Prefer requested vehicle type if specified
        preferred_type = preferences.get("vehicle_type", "").title()
        if preferred_type in self.vehicle_types and preferred_type in suitable_types:
            suitable_types = [preferred_type] + [t for t in suitable_types if t != preferred_type]
        
        for vehicle_type in suitable_types[:3]:  # Limit to 3 options
            vehicle_info = self.vehicle_types[vehicle_type]
            
            # Calculate estimated distance (mock calculation)
            estimated_distance = random.randint(5, 50)
            
            # Calculate pricing
            base_fare = vehicle_info["base_rate"]
            distance_fare = vehicle_info["per_km"] * estimated_distance
            surge_multiplier = city_info["surge_factor"]
            subtotal = (base_fare + distance_fare) * surge_multiplier
            taxes = subtotal * 0.12  # 12% tax
            total_fare = subtotal + taxes
            
            # Simulate availability
            availability = random.choice([True, True, True, False])  # 75% availability
            
            if availability:
                cab_option = {
                    "vehicle_type": vehicle_type,
                    "model": random.choice(vehicle_info["models"]),
                    "capacity": vehicle_info["capacity"],
                    "features": vehicle_info["features"],
                    "description": vehicle_info["description"],
                    "driver_name": random.choice(self.driver_names),
                    "driver_rating": round(random.uniform(4.2, 4.9), 1),
                    "estimated_distance": f"{estimated_distance} km",
                    "estimated_duration": f"{random.randint(15, 90)} min",
                    "pickup_time": pickup_time,
                    "pricing": {
                        "base_fare": f"₹{base_fare}",
                        "distance_fare": f"₹{distance_fare}",
                        "surge_multiplier": f"{surge_multiplier}x",
                        "subtotal": f"₹{int(subtotal)}",
                        "taxes": f"₹{int(taxes)}",
                        "total_fare": f"₹{int(total_fare)}"
                    },
                    "vehicle_number": f"{random.choice(['DL', 'MH', 'KA', 'TN'])}-{random.randint(10, 99)}-{random.choice(['AB', 'CD', 'EF'])}-{random.randint(1000, 9999)}",
                    "eta": f"{random.randint(3, 15)} min"
                }
                available_cabs.append(cab_option)
        
        return available_cabs
    
    def book_cab(self, cab_option: Dict[str, Any], booking_details: Dict[str, Any]) -> Dict[str, Any]:
        """Book a specific cab and return comprehensive booking confirmation"""
        
        self.booking_counter += 1
        booking_id = f"CAB{random.randint(10000, 99999)}{chr(65 + random.randint(0, 25))}{random.randint(10, 99)}"
        confirmation_code = booking_id[-6:]
        
        # Generate comprehensive booking details
        booking_result = {
            "booking_id": booking_id,
            "confirmation_code": confirmation_code,
            "status": "confirmed",
            "vehicle_details": {
                "type": cab_option["vehicle_type"],
                "model": cab_option["model"],
                "number": cab_option["vehicle_number"],
                "capacity": cab_option["capacity"],
                "features": cab_option["features"]
            },
            "driver_details": {
                "name": cab_option["driver_name"],
                "rating": cab_option["driver_rating"],
                "phone": f"+91-{random.randint(70000, 99999)}{random.randint(10000, 99999)}"
            },
            "journey_details": {
                "pickup_location": booking_details["pickup_location"],
                "destination": booking_details["destination"],
                "pickup_time": booking_details["pickup_time"],
                "estimated_distance": cab_option["estimated_distance"],
                "estimated_duration": cab_option["estimated_duration"],
                "passengers": booking_details["passengers"]
            },
            "pricing_breakdown": cab_option["pricing"],
            "booking_timestamp": datetime.now().isoformat(),
            "eta": cab_option["eta"],
            "special_instructions": booking_details.get("special_instructions", "None"),
            "payment_method": booking_details.get("payment_method", "Cash"),
            "booking_type": "comprehensive"
        }
        
        return booking_result


class EnhancedCabAgent(AgentExecutor):
    """Enhanced cab booking agent with comprehensive database and detailed responses"""
    
    def __init__(self):
        self.cab_db = GlobalCabDatabase()
        print("🚗 Enhanced Cab Agent initialized with global database")
        print(f"📊 Supporting {len(self.cab_db.cities)} cities worldwide")
        print(f"🚙 {len(self.cab_db.vehicle_types)} vehicle types available")
    
    def _parse_booking_request(self, message_text: str) -> Dict[str, Any]:
        """Parse booking request from message text"""
        try:
            # Try to parse as JSON first
            if message_text.strip().startswith('{'):
                return json.loads(message_text)
            
            # Extract information from natural language
            booking_info = {
                "pickup_location": "Delhi",  # Default
                "destination": "Airport",    # Default
                "pickup_time": "Now",
                "passengers": 2,
                "preferences": {}
            }
            
            # Simple keyword extraction
            text_lower = message_text.lower()
            
            # Extract cities
            for city in self.cab_db.cities.keys():
                if city.lower() in text_lower:
                    if "from" in text_lower and text_lower.index(city.lower()) > text_lower.index("from"):
                        booking_info["pickup_location"] = city
                    elif "to" in text_lower and text_lower.index(city.lower()) > text_lower.index("to"):
                        booking_info["destination"] = city
            
            # Extract passenger count
            import re
            passenger_match = re.search(r'(\d+)\s*passenger', text_lower)
            if passenger_match:
                booking_info["passengers"] = int(passenger_match.group(1))
            
            # Extract vehicle preference
            for vehicle_type in self.cab_db.vehicle_types.keys():
                if vehicle_type.lower() in text_lower:
                    booking_info["preferences"]["vehicle_type"] = vehicle_type
                    break
            
            return booking_info
            
        except Exception as e:
            print(f"❌ Error parsing booking request: {e}")
            return {
                "pickup_location": "Delhi",
                "destination": "Airport", 
                "pickup_time": "Now",
                "passengers": 2,
                "preferences": {}
            }
    
    def _comprehensive_booking(self, booking_request: Dict[str, Any]) -> str:
        """Process comprehensive cab booking with detailed response"""
        
        pickup_location = booking_request.get("pickup_location", "Delhi")
        destination = booking_request.get("destination", "Airport")
        pickup_time = booking_request.get("pickup_time", "Now")
        passengers = booking_request.get("passengers", 2)
        preferences = booking_request.get("preferences", {})
        
        print(f"🔍 Searching cabs from {pickup_location} to {destination} for {passengers} passengers")
        
        # Search for available cabs
        available_cabs = self.cab_db.search_cabs(
            pickup_location=pickup_location,
            destination=destination,
            pickup_time=pickup_time,
            passengers=passengers,
            preferences=preferences
        )
        
        if not available_cabs:
            return self._generate_no_availability_response(pickup_location, destination, passengers)
        
        # Select best option (first available)
        selected_cab = available_cabs[0]
        
        # Create booking details
        booking_details = {
            "pickup_location": pickup_location,
            "destination": destination,
            "pickup_time": pickup_time,
            "passengers": passengers,
            "special_instructions": preferences.get("special_instructions", ""),
            "payment_method": preferences.get("payment_method", "Cash")
        }
        
        # Book the cab
        booking_result = self.cab_db.book_cab(selected_cab, booking_details)
        
        # Generate comprehensive response
        return self._format_booking_confirmation(booking_result)
    
    def _generate_no_availability_response(self, pickup_location: str, destination: str, passengers: int) -> str:
        """Generate response when no cabs are available"""
        return f"""🚗 **CAB BOOKING STATUS** 🚗

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ **NO CABS AVAILABLE**

📍 **Route:** {pickup_location} → {destination}
👥 **Passengers:** {passengers}

🔄 **ALTERNATIVE OPTIONS:**
• Try booking for a later time
• Consider different vehicle types
• Check nearby pickup locations

📞 **Contact Support:** +91-1800-CAB-HELP
🕒 **Booking attempted:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    def _format_booking_confirmation(self, booking_result: Dict[str, Any]) -> str:
        """Format comprehensive booking confirmation"""
        
        vehicle = booking_result["vehicle_details"]
        driver = booking_result["driver_details"]
        journey = booking_result["journey_details"]
        pricing = booking_result["pricing_breakdown"]
        
        confirmation = f"""🚗 **CAB BOOKING CONFIRMED** 🚗

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎫 **Booking Reference:** {booking_result['booking_id']}
🔑 **Confirmation Code:** {booking_result['confirmation_code']}

🚙 **VEHICLE DETAILS**
• **Type:** {vehicle['type']} - {vehicle['model']}
• **Vehicle Number:** {vehicle['number']}
• **Capacity:** {vehicle['capacity']} passengers
• **Features:** {', '.join(vehicle['features'])}

👨‍✈️ **DRIVER INFORMATION**
• **Name:** {driver['name']}
• **Rating:** ⭐ {driver['rating']}/5.0
• **Contact:** {driver['phone']}

🗺️ **JOURNEY DETAILS**
• **Pickup:** {journey['pickup_location']}
• **Destination:** {journey['destination']}
• **Pickup Time:** {journey['pickup_time']}
• **Distance:** {journey['estimated_distance']}
• **Duration:** {journey['estimated_duration']}
• **Passengers:** {journey['passengers']}

💰 **PRICING BREAKDOWN**
• **Base Fare:** {pricing['base_fare']}
• **Distance Charge:** {pricing['distance_fare']}
• **Surge Multiplier:** {pricing['surge_multiplier']}
• **Subtotal:** {pricing['subtotal']}
• **Taxes (12%):** {pricing['taxes']}
• **TOTAL FARE:** {pricing['total_fare']}

⏰ **ETA:** {booking_result['eta']}
💳 **Payment:** {booking_result.get('payment_method', 'Cash')}

🔧 **System Status:** Booking processed at {booking_result['booking_timestamp'][:19]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **STATUS: CONFIRMED & DRIVER ASSIGNED** ✅"""
        
        return confirmation
    
    @override
    async def execute(self, request, event_queue: EventQueue):
        """Execute cab booking with comprehensive processing"""
        try:
            # Extract user message text from request (following enhanced flight agent pattern)
            try:
                if hasattr(request, 'message') and request.message:
                    if hasattr(request.message, 'parts') and request.message.parts:
                        first_part = request.message.parts[0]
                        if hasattr(first_part, 'text'):
                            user_message_text = first_part.text
                        elif hasattr(first_part, 'content'):
                            user_message_text = first_part.content
                        elif hasattr(first_part, 'root') and hasattr(first_part.root, 'text'):
                            user_message_text = first_part.root.text
                        else:
                            # Extract from string representation
                            import re
                            part_str = str(first_part)
                            if "text='" in part_str:
                                text_start = part_str.find("text='") + 6
                                remaining = part_str[text_start:]
                                text_end = remaining.rfind("')")
                                if text_end > 0:
                                    user_message_text = remaining[:text_end]
                                    user_message_text = user_message_text.replace("\\'", "'").replace("\\n", "\n")
                                else:
                                    user_message_text = part_str
                            else:
                                user_message_text = part_str
                    else:
                        user_message_text = str(request.message)
                elif hasattr(request, 'messages') and request.messages:
                    user_message_text = request.messages[0].parts[0].text
                else:
                    user_message_text = str(request)
            except Exception as e:
                print(f"Error extracting message: {e}")
                user_message_text = str(request)
                
            print(f"🚗 Enhanced Cab agent received request: {user_message_text}")
            
            # Parse the booking request
            booking_request = self._parse_booking_request(user_message_text)
            print(f"📋 Parsed booking request: {booking_request}")
            
            # Process comprehensive booking
            booking_response = self._comprehensive_booking(booking_request)
            
            # Create response message
            response_message = Message(
                message_id=str(uuid.uuid4()),
                role="agent",
                parts=[TextPart(text=booking_response)],
            )
            
            # Send response and mark as completed
            await event_queue.enqueue_event(response_message)
            await event_queue.enqueue_event(TaskStatus(state=TaskState.completed))
            
            print("✅ Enhanced cab booking response sent successfully")
            
        except Exception as e:
            print(f"❌ Error in enhanced cab booking: {e}")
            error_message = Message(
                message_id=str(uuid.uuid4()),
                role="agent",
                parts=[TextPart(text=f"Sorry, there was an error processing your cab booking: {str(e)}")],
            )
            await event_queue.enqueue_event(error_message)
            await event_queue.enqueue_event(TaskStatus(state=TaskState.failed))
    
    @override
    async def cancel(self, request, event_queue: EventQueue):
        """Handle task cancellation"""
        print(f"🚫 Cancelling enhanced cab booking")
        await event_queue.enqueue_event(TaskStatus(state=TaskState.canceled))


def create_app():
    """Factory function to create the enhanced cab booking application"""
    agent_card = AgentCard(
        name="EnhancedCabBookingAgent",
        description="Enhanced cab booking agent with global database and comprehensive responses",
        url="http://localhost:5001/",
        version="2.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="book_cab",
                name="book_cab",
                description="Book cabs with comprehensive details including vehicle types, driver information, pricing breakdown, and real-time availability across 30+ global cities",
                input_modes=["text"],
                output_modes=["text"],
                tags=["cab", "booking", "transport"]
            )
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"]
    )

    request_handler = DefaultRequestHandler(
        agent_executor=EnhancedCabAgent(),
        task_store=InMemoryTaskStore(),
    )
    
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    # Build and return the Starlette app
    return a2a_app.build()

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
        port=5001,
        log_level="info"
    )

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
        port=5001,
        log_level="info"
    )
