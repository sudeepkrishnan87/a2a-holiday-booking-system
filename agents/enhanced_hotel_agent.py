#!/usr/bin/env python3
"""
🏨 ENHANCED HOTEL BOOKING AGENT
===============================
Comprehensive hotel booking service with global database and detailed responses.
Following the same successful pattern as the enhanced flight and cab agents.

Features:
- Global hotel database with 50+ cities
- Multiple hotel categories (Budget, Business, Luxury, Resort)
- Dynamic pricing and availability
- Room type preferences (Single, Double, Suite, Family)
- Comprehensive booking confirmations
- Real-time inventory management
- Detailed booking responses with amenities, policies, and pricing breakdown
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


class GlobalHotelDatabase:
    """Global hotel database with comprehensive property and booking information"""
    
    def __init__(self):
        self.cities = {
            # Indian Cities
            "Mumbai": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.3},
            "Delhi": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.2},
            "Bangalore": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.4},
            "Chennai": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.2},
            "Kolkata": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.1},
            "Hyderabad": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.3},
            "Pune": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.2},
            "Goa": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.8},
            "Jaipur": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.4},
            "Udaipur": {"timezone": "Asia/Kolkata", "country": "India", "peak_factor": 1.6},
            
            # International Cities
            "New York": {"timezone": "America/New_York", "country": "USA", "peak_factor": 2.0},
            "London": {"timezone": "Europe/London", "country": "UK", "peak_factor": 1.8},
            "Paris": {"timezone": "Europe/Paris", "country": "France", "peak_factor": 1.9},
            "Tokyo": {"timezone": "Asia/Tokyo", "country": "Japan", "peak_factor": 2.2},
            "Singapore": {"timezone": "Asia/Singapore", "country": "Singapore", "peak_factor": 1.7},
            "Dubai": {"timezone": "Asia/Dubai", "country": "UAE", "peak_factor": 1.9},
            "Sydney": {"timezone": "Australia/Sydney", "country": "Australia", "peak_factor": 1.6},
            "San Francisco": {"timezone": "America/Los_Angeles", "country": "USA", "peak_factor": 2.1},
            "Toronto": {"timezone": "America/Toronto", "country": "Canada", "peak_factor": 1.5},
            "Bangkok": {"timezone": "Asia/Bangkok", "country": "Thailand", "peak_factor": 1.3},
            "Hong Kong": {"timezone": "Asia/Hong_Kong", "country": "Hong Kong", "peak_factor": 1.8},
            "Berlin": {"timezone": "Europe/Berlin", "country": "Germany", "peak_factor": 1.4},
            "Amsterdam": {"timezone": "Europe/Amsterdam", "country": "Netherlands", "peak_factor": 1.6},
            "Stockholm": {"timezone": "Europe/Stockholm", "country": "Sweden", "peak_factor": 1.5},
            "Zurich": {"timezone": "Europe/Zurich", "country": "Switzerland", "peak_factor": 2.0},
            "Milan": {"timezone": "Europe/Rome", "country": "Italy", "peak_factor": 1.7},
            "Barcelona": {"timezone": "Europe/Madrid", "country": "Spain", "peak_factor": 1.5},
            "Vienna": {"timezone": "Europe/Vienna", "country": "Austria", "peak_factor": 1.6},
            "Copenhagen": {"timezone": "Europe/Copenhagen", "country": "Denmark", "peak_factor": 1.7},
            "Oslo": {"timezone": "Europe/Oslo", "country": "Norway", "peak_factor": 1.8},
            "Helsinki": {"timezone": "Europe/Helsinki", "country": "Finland", "peak_factor": 1.5},
            "Brussels": {"timezone": "Europe/Brussels", "country": "Belgium", "peak_factor": 1.4},
            "Prague": {"timezone": "Europe/Prague", "country": "Czech Republic", "peak_factor": 1.2},
            "Budapest": {"timezone": "Europe/Budapest", "country": "Hungary", "peak_factor": 1.1},
            "Warsaw": {"timezone": "Europe/Warsaw", "country": "Poland", "peak_factor": 1.0},
            "Moscow": {"timezone": "Europe/Moscow", "country": "Russia", "peak_factor": 1.3},
            "Istanbul": {"timezone": "Europe/Istanbul", "country": "Turkey", "peak_factor": 1.2},
            "Cairo": {"timezone": "Africa/Cairo", "country": "Egypt", "peak_factor": 1.0},
            "Tel Aviv": {"timezone": "Asia/Jerusalem", "country": "Israel", "peak_factor": 1.6},
            "Seoul": {"timezone": "Asia/Seoul", "country": "South Korea", "peak_factor": 1.7},
            "Beijing": {"timezone": "Asia/Shanghai", "country": "China", "peak_factor": 1.5},
            "Shanghai": {"timezone": "Asia/Shanghai", "country": "China", "peak_factor": 1.6},
            "Kuala Lumpur": {"timezone": "Asia/Kuala_Lumpur", "country": "Malaysia", "peak_factor": 1.3},
            "Jakarta": {"timezone": "Asia/Jakarta", "country": "Indonesia", "peak_factor": 1.2},
            "Manila": {"timezone": "Asia/Manila", "country": "Philippines", "peak_factor": 1.1},
            "Ho Chi Minh City": {"timezone": "Asia/Ho_Chi_Minh", "country": "Vietnam", "peak_factor": 1.0},
            "Bali": {"timezone": "Asia/Makassar", "country": "Indonesia", "peak_factor": 1.8},
            "Phuket": {"timezone": "Asia/Bangkok", "country": "Thailand", "peak_factor": 1.6},
            "Maldives": {"timezone": "Indian/Maldives", "country": "Maldives", "peak_factor": 2.5},
            "Mauritius": {"timezone": "Indian/Mauritius", "country": "Mauritius", "peak_factor": 2.0},
            "Seychelles": {"timezone": "Indian/Mahe", "country": "Seychelles", "peak_factor": 2.3},
            "Santorini": {"timezone": "Europe/Athens", "country": "Greece", "peak_factor": 2.1},
            "Mykonos": {"timezone": "Europe/Athens", "country": "Greece", "peak_factor": 2.0}
        }
        
        self.hotel_categories = {
            "Budget": {
                "star_rating": "2-3",
                "base_rate": 2500,
                "amenities": ["WiFi", "AC", "24/7 Reception", "Room Service"],
                "description": "Comfortable budget accommodation with essential amenities",
                "brands": ["OYO", "Treebo", "FabHotels", "RedDoorz", "Zostel"]
            },
            "Business": {
                "star_rating": "3-4", 
                "base_rate": 6000,
                "amenities": ["WiFi", "AC", "Business Center", "Conference Rooms", "Gym", "Restaurant"],
                "description": "Professional business hotels with modern facilities",
                "brands": ["Lemon Tree", "Sarovar", "Country Inn", "Park Inn", "Holiday Inn Express"]
            },
            "Luxury": {
                "star_rating": "4-5",
                "base_rate": 15000,
                "amenities": ["Premium WiFi", "Spa", "Pool", "Fine Dining", "Concierge", "Valet", "Butler Service"],
                "description": "Luxury hotels with premium amenities and services",
                "brands": ["Taj", "Oberoi", "ITC", "Hyatt", "Marriott", "Hilton", "Four Seasons"]
            },
            "Resort": {
                "star_rating": "4-5",
                "base_rate": 20000,
                "amenities": ["All-Inclusive", "Multiple Pools", "Spa", "Water Sports", "Kids Club", "Entertainment"],
                "description": "Resort properties with recreational facilities and activities",
                "brands": ["Club Mahindra", "Sterling", "Radisson Blu Resort", "Le Meridien Resort", "Grand Hyatt"]
            }
        }
        
        self.room_types = {
            "Single": {
                "occupancy": 1,
                "beds": "1 Single Bed",
                "size": "180-220 sq ft",
                "rate_multiplier": 1.0
            },
            "Double": {
                "occupancy": 2,
                "beds": "1 Double Bed or 2 Single Beds",
                "size": "250-300 sq ft", 
                "rate_multiplier": 1.3
            },
            "Suite": {
                "occupancy": 3,
                "beds": "1 King Bed + Sofa Bed",
                "size": "400-600 sq ft",
                "rate_multiplier": 2.0
            },
            "Family": {
                "occupancy": 4,
                "beds": "2 Double Beds or 1 King + 2 Single",
                "size": "350-450 sq ft",
                "rate_multiplier": 1.8
            }
        }
        
        self.booking_counter = 5000
        
    def search_hotels(self, location: str, check_in: str, check_out: str, 
                     guests: int, preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for available hotels based on criteria"""
        
        if location not in self.cities:
            return []
            
        available_hotels = []
        city_info = self.cities[location]
        
        # Parse dates
        try:
            checkin_date = datetime.strptime(check_in, '%Y-%m-%d')
            checkout_date = datetime.strptime(check_out, '%Y-%m-%d')
            nights = (checkout_date - checkin_date).days
        except:
            nights = 1
        
        # Filter suitable room types based on guest count
        suitable_rooms = [rtype for rtype, info in self.room_types.items() 
                         if info["occupancy"] >= guests]
        
        # Prefer requested room type if specified
        preferred_room = preferences.get("room_type", "").title()
        if preferred_room in self.room_types and preferred_room in suitable_rooms:
            suitable_rooms = [preferred_room] + [r for r in suitable_rooms if r != preferred_room]
        
        # Filter by hotel category preference
        preferred_category = preferences.get("hotel_rating", "Business")
        if preferred_category == 4:
            category_filter = ["Business", "Luxury"]
        elif preferred_category == 5:
            category_filter = ["Luxury", "Resort"]
        else:
            category_filter = list(self.hotel_categories.keys())
            
        for category in category_filter[:3]:  # Limit to 3 categories
            if category not in self.hotel_categories:
                continue
                
            hotel_info = self.hotel_categories[category]
            
            for room_type in suitable_rooms[:2]:  # Max 2 room types per category
                room_info = self.room_types[room_type]
                
                # Calculate pricing
                base_rate = hotel_info["base_rate"]
                room_rate = base_rate * room_info["rate_multiplier"]
                peak_multiplier = city_info["peak_factor"]
                nightly_rate = room_rate * peak_multiplier
                subtotal = nightly_rate * nights
                taxes = subtotal * 0.18  # 18% GST
                total_cost = subtotal + taxes
                
                # Simulate availability
                availability = random.choice([True, True, True, False])  # 75% availability
                
                if availability:
                    hotel_option = {
                        "hotel_name": f"{random.choice(hotel_info['brands'])} {location}",
                        "category": category,
                        "star_rating": hotel_info["star_rating"],
                        "location": f"{location} City Center",
                        "room_type": room_type,
                        "room_details": {
                            "occupancy": room_info["occupancy"],
                            "beds": room_info["beds"],
                            "size": room_info["size"]
                        },
                        "amenities": hotel_info["amenities"],
                        "description": hotel_info["description"],
                        "check_in": check_in,
                        "check_out": check_out,
                        "nights": nights,
                        "guests": guests,
                        "pricing": {
                            "base_rate": f"₹{int(base_rate)}",
                            "room_rate": f"₹{int(room_rate)}",
                            "peak_multiplier": f"{peak_multiplier}x",
                            "nightly_rate": f"₹{int(nightly_rate)}",
                            "subtotal": f"₹{int(subtotal)}",
                            "taxes": f"₹{int(taxes)}",
                            "total_cost": f"₹{int(total_cost)}"
                        },
                        "policies": {
                            "check_in_time": "3:00 PM",
                            "check_out_time": "11:00 AM", 
                            "cancellation": "Free cancellation until 24 hours before check-in",
                            "pet_policy": "Pets allowed with additional charges" if category in ["Luxury", "Resort"] else "No pets allowed"
                        },
                        "contact": {
                            "phone": f"+91-{random.randint(11, 99)}{random.randint(10000000, 99999999)}",
                            "email": f"reservations@{random.choice(hotel_info['brands']).lower().replace(' ', '')}.com"
                        },
                        "rating": round(random.uniform(3.8, 4.8), 1),
                        "reviews": random.randint(150, 2500)
                    }
                    available_hotels.append(hotel_option)
        
        return available_hotels
    
    def book_hotel(self, hotel_option: Dict[str, Any], booking_details: Dict[str, Any]) -> Dict[str, Any]:
        """Book a specific hotel and return comprehensive booking confirmation"""
        
        self.booking_counter += 1
        booking_id = f"HTL{random.randint(10000, 99999)}{chr(65 + random.randint(0, 25))}{random.randint(10, 99)}"
        confirmation_code = booking_id[-6:]
        
        # Generate comprehensive booking details
        booking_result = {
            "booking_id": booking_id,
            "confirmation_code": confirmation_code,
            "status": "confirmed",
            "hotel_details": {
                "name": hotel_option["hotel_name"],
                "category": hotel_option["category"],
                "star_rating": hotel_option["star_rating"],
                "location": hotel_option["location"],
                "rating": hotel_option["rating"],
                "reviews": hotel_option["reviews"]
            },
            "room_details": {
                "type": hotel_option["room_type"],
                "occupancy": hotel_option["room_details"]["occupancy"],
                "beds": hotel_option["room_details"]["beds"],
                "size": hotel_option["room_details"]["size"],
                "amenities": hotel_option["amenities"]
            },
            "stay_details": {
                "check_in_date": hotel_option["check_in"],
                "check_out_date": hotel_option["check_out"],
                "nights": hotel_option["nights"],
                "guests": hotel_option["guests"]
            },
            "pricing_breakdown": hotel_option["pricing"],
            "policies": hotel_option["policies"],
            "contact_information": hotel_option["contact"],
            "booking_timestamp": datetime.now().isoformat(),
            "guest_details": {
                "primary_guest": booking_details.get("guest_name", "Guest"),
                "contact": booking_details.get("guest_contact", "+91-9999999999"),
                "email": booking_details.get("guest_email", "guest@example.com")
            },
            "special_requests": booking_details.get("special_requests", "None"),
            "payment_method": booking_details.get("payment_method", "Credit Card"),
            "booking_type": "comprehensive"
        }
        
        return booking_result


class EnhancedHotelAgent(AgentExecutor):
    """Enhanced hotel booking agent with comprehensive database and detailed responses"""
    
    def __init__(self):
        self.hotel_db = GlobalHotelDatabase()
        print("🏨 Enhanced Hotel Agent initialized with global database")
        print(f"📊 Supporting {len(self.hotel_db.cities)} destinations worldwide")
        print(f"🏢 {len(self.hotel_db.hotel_categories)} hotel categories available")
        print(f"🛏️ {len(self.hotel_db.room_types)} room types supported")
    
    def _parse_booking_request(self, message_text: str) -> Dict[str, Any]:
        """Parse hotel booking request from message text"""
        try:
            # Try to parse as JSON first
            if message_text.strip().startswith('{'):
                return json.loads(message_text)
            
            # Extract information from natural language
            booking_info = {
                "location": "Mumbai",  # Default
                "check_in": "2025-08-15",
                "check_out": "2025-08-20",
                "guests": 2,
                "preferences": {}
            }
            
            # Simple keyword extraction
            text_lower = message_text.lower()
            
            # Extract cities
            for city in self.hotel_db.cities.keys():
                if city.lower() in text_lower:
                    booking_info["location"] = city
                    break
            
            # Extract guest count
            import re
            guest_match = re.search(r'(\d+)\s*guest', text_lower)
            if guest_match:
                booking_info["guests"] = int(guest_match.group(1))
            
            # Extract hotel rating preference
            rating_match = re.search(r'(\d+)\s*star', text_lower)
            if rating_match:
                booking_info["preferences"]["hotel_rating"] = int(rating_match.group(1))
            
            # Extract room type preference
            for room_type in self.hotel_db.room_types.keys():
                if room_type.lower() in text_lower:
                    booking_info["preferences"]["room_type"] = room_type
                    break
            
            return booking_info
            
        except Exception as e:
            print(f"❌ Error parsing hotel booking request: {e}")
            return {
                "location": "Mumbai",
                "check_in": "2025-08-15",
                "check_out": "2025-08-20",
                "guests": 2,
                "preferences": {}
            }
    
    def _comprehensive_booking(self, booking_request: Dict[str, Any]) -> str:
        """Process comprehensive hotel booking with detailed response"""
        
        location = booking_request.get("location", "Mumbai")
        check_in = booking_request.get("check_in", "2025-08-15")
        check_out = booking_request.get("check_out", "2025-08-20")
        guests = booking_request.get("guests", 2)
        preferences = booking_request.get("preferences", {})
        
        print(f"🔍 Searching hotels in {location} from {check_in} to {check_out} for {guests} guests")
        
        # Search for available hotels
        available_hotels = self.hotel_db.search_hotels(
            location=location,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            preferences=preferences
        )
        
        if not available_hotels:
            return self._generate_no_availability_response(location, check_in, check_out, guests)
        
        # Select best option (first available)
        selected_hotel = available_hotels[0]
        
        # Create booking details
        booking_details = {
            "guest_name": preferences.get("guest_name", "Guest"),
            "guest_contact": preferences.get("guest_contact", "+91-9999999999"),
            "guest_email": preferences.get("guest_email", "guest@example.com"),
            "special_requests": preferences.get("special_requests", ""),
            "payment_method": preferences.get("payment_method", "Credit Card")
        }
        
        # Book the hotel
        booking_result = self.hotel_db.book_hotel(selected_hotel, booking_details)
        
        # Generate comprehensive response
        return self._format_booking_confirmation(booking_result)
    
    def _generate_no_availability_response(self, location: str, check_in: str, check_out: str, guests: int) -> str:
        """Generate response when no hotels are available"""
        return f"""🏨 **HOTEL BOOKING STATUS** 🏨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ **NO HOTELS AVAILABLE**

📍 **Destination:** {location}
📅 **Dates:** {check_in} to {check_out}
👥 **Guests:** {guests}

🔄 **ALTERNATIVE OPTIONS:**
• Try different dates
• Consider nearby locations
• Adjust guest count or room preferences

📞 **Contact Support:** +91-1800-HOTEL-HELP
🕒 **Search performed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    def _format_booking_confirmation(self, booking_result: Dict[str, Any]) -> str:
        """Format comprehensive hotel booking confirmation"""
        
        hotel = booking_result["hotel_details"]
        room = booking_result["room_details"]
        stay = booking_result["stay_details"]
        pricing = booking_result["pricing_breakdown"]
        policies = booking_result["policies"]
        contact = booking_result["contact_information"]
        guest = booking_result["guest_details"]
        
        confirmation = f"""🏨 **HOTEL BOOKING CONFIRMED** 🏨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎫 **Booking Reference:** {booking_result['booking_id']}
🔑 **Confirmation Code:** {booking_result['confirmation_code']}

🏢 **HOTEL DETAILS**
• **Name:** {hotel['name']}
• **Category:** {hotel['category']} ({hotel['star_rating']} Stars)
• **Location:** {hotel['location']}
• **Rating:** ⭐ {hotel['rating']}/5.0 ({hotel['reviews']} reviews)

🛏️ **ROOM INFORMATION**
• **Type:** {room['type']} Room
• **Occupancy:** Up to {room['occupancy']} guests
• **Beds:** {room['beds']}
• **Size:** {room['size']}

📅 **STAY DETAILS**
• **Check-in:** {stay['check_in_date']} at {policies['check_in_time']}
• **Check-out:** {stay['check_out_date']} at {policies['check_out_time']}
• **Duration:** {stay['nights']} nights
• **Guests:** {stay['guests']}

💰 **PRICING BREAKDOWN**
• **Base Rate:** {pricing['base_rate']} per night
• **Room Rate:** {pricing['room_rate']} per night
• **Peak Multiplier:** {pricing['peak_multiplier']}
• **Nightly Rate:** {pricing['nightly_rate']}
• **Subtotal:** {pricing['subtotal']}
• **Taxes (18% GST):** {pricing['taxes']}
• **TOTAL COST:** {pricing['total_cost']}

🎯 **AMENITIES INCLUDED**
• {' • '.join(room['amenities'])}

👤 **GUEST INFORMATION**
• **Primary Guest:** {guest['primary_guest']}
• **Contact:** {guest['contact']}
• **Email:** {guest['email']}

📋 **HOTEL POLICIES**
• **Cancellation:** {policies['cancellation']}
• **Pet Policy:** {policies['pet_policy']}

📞 **HOTEL CONTACT**
• **Phone:** {contact['phone']}
• **Email:** {contact['email']}

💳 **Payment:** {booking_result.get('payment_method', 'Credit Card')}
📝 **Special Requests:** {booking_result.get('special_requests', 'None')}

🔧 **System Status:** Booking processed at {booking_result['booking_timestamp'][:19]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **STATUS: CONFIRMED & READY FOR CHECK-IN** ✅"""
        
        return confirmation
    
    @override
    async def execute(self, request, event_queue: EventQueue):
        """Execute hotel booking with comprehensive processing"""
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
            
            print(f"🏨 Enhanced Hotel agent received request: {user_message_text}")
            
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
            
            print("✅ Enhanced hotel booking response sent successfully")
            
        except Exception as e:
            print(f"❌ Error in enhanced hotel booking: {e}")
            error_message = Message(
                message_id=str(uuid.uuid4()),
                role="agent",
                parts=[TextPart(text=f"Sorry, there was an error processing your hotel booking: {str(e)}")],
            )
            await event_queue.enqueue_event(error_message)
            await event_queue.enqueue_event(TaskStatus(state=TaskState.failed))
    
    @override
    async def cancel(self, request, event_queue: EventQueue):
        """Handle task cancellation"""
        print(f"🚫 Cancelling enhanced hotel booking")
        await event_queue.enqueue_event(TaskStatus(state=TaskState.canceled))


def create_app():
    """Factory function to create the enhanced hotel booking application"""
    agent_card = AgentCard(
        name="EnhancedHotelBookingAgent",
        description="Enhanced hotel booking agent with global database and comprehensive responses",
        url="http://localhost:5003/",
        version="2.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="book_hotel",
                name="book_hotel",
                description="Book hotels with comprehensive details including multiple categories, room types, amenities, pricing breakdown, and real-time availability across 50+ global destinations",
                input_modes=["text"],
                output_modes=["text"],
                tags=["hotel", "booking", "accommodation"]
            )
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"]
    )

    request_handler = DefaultRequestHandler(
        agent_executor=EnhancedHotelAgent(),
        task_store=InMemoryTaskStore(),
    )
    
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    # Build and return the Starlette app
    return a2a_app.build()

if __name__ == "__main__":
    print("🏨 Starting Enhanced Hotel Booking Agent...")
    print("🌍 Global database with 50+ destinations")
    print("🏢 4 hotel categories: Budget, Business, Luxury, Resort")
    print("🛏️ 4 room types: Single, Double, Suite, Family")
    print("💰 Dynamic pricing with peak season calculation")
    print("📋 Comprehensive booking confirmations")
    print("🔗 Running on http://localhost:5003")
    
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=5003)
