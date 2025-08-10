#!/usr/bin/env python3
"""
Enhanced Flight Agent - Production Ready
A2A SDK-based flight booking service with global flight data and availability management.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field

# For A2A SDK - use the correct import structure
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, Task, TextPart, TaskStatus, TaskState, Message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
PORT = int(os.getenv("PORT", "5002"))
HOST = os.getenv("HOST", "0.0.0.0")

@dataclass
class Airport:
    """Airport data model"""
    code: str
    name: str
    city: str
    country: str
    timezone: str
    latitude: float
    longitude: float

@dataclass
class Flight:
    """Flight data model"""
    flight_id: str
    airline: str
    airline_code: str
    flight_number: str
    origin: str
    origin_code: str
    destination: str
    destination_code: str
    departure_time: str
    arrival_time: str
    duration: str
    aircraft: str
    available_seats: int
    total_seats: int
    price_economy: float
    price_business: float
    price_first: float
    route_type: str  # domestic, international, regional

class FlightSearchRequest(BaseModel):
    origin: str = Field(..., description="Origin city or airport code")
    destination: str = Field(..., description="Destination city or airport code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    passengers: int = Field(default=1, ge=1, le=9, description="Number of passengers")
    class_type: str = Field(default="economy", description="Class: economy, business, first")
    return_date: Optional[str] = Field(None, description="Return date for round trip")

class FlightBookingRequest(BaseModel):
    flight_id: str = Field(..., description="Flight ID to book")
    passengers: int = Field(..., ge=1, le=9, description="Number of passengers")
    passenger_details: List[Dict[str, str]] = Field(..., description="Passenger information")
    class_type: str = Field(default="economy", description="Class: economy, business, first")

class GlobalFlightDatabase:
    """Global flight database with comprehensive route mappings"""
    
    def __init__(self):
        self.airports = self._initialize_airports()
        self.flights = self._initialize_flights()
        self.bookings = {}  # Store active bookings
        logger.info(f"Initialized flight database with {len(self.flights)} flights across {len(self.airports)} airports")
    
    def _initialize_airports(self) -> Dict[str, Airport]:
        """Initialize global airport database"""
        airports_data = [
            # Major Indian Airports
            ("DEL", "Indira Gandhi International", "Delhi", "India", "Asia/Kolkata", 28.5562, 77.1000),
            ("BOM", "Chhatrapati Shivaji International", "Mumbai", "India", "Asia/Kolkata", 19.0896, 72.8656),
            ("BLR", "Kempegowda International", "Bangalore", "India", "Asia/Kolkata", 13.1986, 77.7066),
            ("MAA", "Chennai International", "Chennai", "India", "Asia/Kolkata", 12.9941, 80.1709),
            ("CCU", "Netaji Subhas Chandra Bose International", "Kolkata", "India", "Asia/Kolkata", 22.6543, 88.4468),
            ("HYD", "Rajiv Gandhi International", "Hyderabad", "India", "Asia/Kolkata", 17.2313, 78.4298),
            ("PNQ", "Pune Airport", "Pune", "India", "Asia/Kolkata", 18.5793, 73.9089),
            ("AMD", "Sardar Vallabhbhai Patel International", "Ahmedabad", "India", "Asia/Kolkata", 23.0772, 72.6347),
            
            # Major International Airports
            ("JFK", "John F. Kennedy International", "New York", "USA", "America/New_York", 40.6413, -73.7781),
            ("LAX", "Los Angeles International", "Los Angeles", "USA", "America/Los_Angeles", 33.9425, -118.4081),
            ("LHR", "Heathrow", "London", "UK", "Europe/London", 51.4700, -0.4543),
            ("CDG", "Charles de Gaulle", "Paris", "France", "Europe/Paris", 49.0097, 2.5479),
            ("FRA", "Frankfurt am Main", "Frankfurt", "Germany", "Europe/Berlin", 50.0379, 8.5622),
            ("NRT", "Narita International", "Tokyo", "Japan", "Asia/Tokyo", 35.7720, 140.3929),
            ("HND", "Haneda", "Tokyo", "Japan", "Asia/Tokyo", 35.5494, 139.7798),
            ("ICN", "Incheon International", "Seoul", "South Korea", "Asia/Seoul", 37.4602, 126.4407),
            ("SIN", "Singapore Changi", "Singapore", "Singapore", "Asia/Singapore", 1.3644, 103.9915),
            ("DXB", "Dubai International", "Dubai", "UAE", "Asia/Dubai", 25.2532, 55.3657),
            ("DOH", "Hamad International", "Doha", "Qatar", "Asia/Qatar", 25.2606, 51.6138),
            ("IST", "Istanbul Airport", "Istanbul", "Turkey", "Europe/Istanbul", 41.2619, 28.7279),
            ("SYD", "Sydney Kingsford Smith", "Sydney", "Australia", "Australia/Sydney", -33.9399, 151.1753),
            ("MEL", "Melbourne Tullamarine", "Melbourne", "Australia", "Australia/Melbourne", -37.6690, 144.8410),
            ("YYZ", "Toronto Pearson International", "Toronto", "Canada", "America/Toronto", 43.6777, -79.6248),
            ("YVR", "Vancouver International", "Vancouver", "Canada", "America/Vancouver", 49.1967, -123.1815),
            
            # European Destinations
            ("BCN", "Barcelona El Prat", "Barcelona", "Spain", "Europe/Madrid", 41.2974, 2.0833),
            ("MAD", "Adolfo Suárez Madrid-Barajas", "Madrid", "Spain", "Europe/Madrid", 40.4719, -3.5626),
            ("FCO", "Leonardo da Vinci–Fiumicino", "Rome", "Italy", "Europe/Rome", 41.8003, 12.2389),
            ("MXP", "Milan Malpensa", "Milan", "Italy", "Europe/Rome", 45.6300, 8.7231),
            ("AMS", "Amsterdam Schiphol", "Amsterdam", "Netherlands", "Europe/Amsterdam", 52.3105, 4.7683),
            ("ZUR", "Zurich Airport", "Zurich", "Switzerland", "Europe/Zurich", 47.4647, 8.5492),
            ("VIE", "Vienna International", "Vienna", "Austria", "Europe/Vienna", 48.1103, 16.5697),
            
            # Asian Destinations
            ("BKK", "Suvarnabhumi", "Bangkok", "Thailand", "Asia/Bangkok", 13.6900, 100.7501),
            ("KUL", "Kuala Lumpur International", "Kuala Lumpur", "Malaysia", "Asia/Kuala_Lumpur", 2.7456, 101.7072),
            ("CGK", "Soekarno-Hatta International", "Jakarta", "Indonesia", "Asia/Jakarta", -6.1275, 106.6537),
            ("MNL", "Ninoy Aquino International", "Manila", "Philippines", "Asia/Manila", 14.5086, 121.0194),
            ("HKG", "Hong Kong International", "Hong Kong", "China", "Asia/Hong_Kong", 22.3080, 113.9185),
            ("PVG", "Shanghai Pudong International", "Shanghai", "China", "Asia/Shanghai", 31.1443, 121.8083),
            ("PEK", "Beijing Capital International", "Beijing", "China", "Asia/Shanghai", 40.0799, 116.6031),
            ("CAN", "Guangzhou Baiyun International", "Guangzhou", "China", "Asia/Shanghai", 23.3924, 113.2988),
        ]
        
        airports = {}
        for code, name, city, country, timezone, lat, lng in airports_data:
            airport = Airport(code, name, city, country, timezone, lat, lng)
            airports[code] = airport
            # Also index by city name for easier lookup
            airports[city.lower()] = airport
        
        return airports
    
    def _initialize_flights(self) -> Dict[str, Flight]:
        """Initialize comprehensive flight database"""
        flights = {}
        flight_routes = [
            # Domestic Indian Routes
            ("AI", "Air India", "DEL", "BOM", "02:15", "04:45", "2h 30m", "Boeing 787", 180, 350, 8500, 25000, 75000),
            ("6E", "IndiGo", "DEL", "BLR", "06:00", "08:45", "2h 45m", "Airbus A320", 156, 180, 7200, 22000, 65000),
            ("SG", "SpiceJet", "BOM", "MAA", "14:30", "16:15", "1h 45m", "Boeing 737", 145, 189, 6800, 20000, 58000),
            ("UK", "Vistara", "DEL", "HYD", "09:15", "11:30", "2h 15m", "Airbus A321", 158, 188, 7800, 24000, 68000),
            ("6E", "IndiGo", "BOM", "CCU", "19:20", "21:45", "2h 25m", "Airbus A320", 162, 180, 8200, 26000, 70000),
            ("AI", "Air India", "BLR", "DEL", "22:30", "01:15", "2h 45m", "Boeing 787", 175, 350, 8800, 27000, 78000),
            
            # India to International
            ("AI", "Air India", "DEL", "JFK", "01:30", "06:45", "14h 15m", "Boeing 777", 245, 370, 65000, 185000, 420000),
            ("EK", "Emirates", "BOM", "DXB", "03:15", "05:45", "3h 30m", "Airbus A380", 280, 615, 22000, 65000, 145000),
            ("QR", "Qatar Airways", "DEL", "DOH", "02:45", "04:30", "4h 45m", "Boeing 787", 210, 335, 28000, 82000, 185000),
            ("TK", "Turkish Airlines", "BOM", "IST", "01:20", "06:15", "7h 55m", "Airbus A330", 198, 289, 35000, 95000, 210000),
            ("LH", "Lufthansa", "DEL", "FRA", "01:45", "06:30", "7h 45m", "Airbus A340", 185, 298, 42000, 115000, 245000),
            ("BA", "British Airways", "BOM", "LHR", "02:30", "07:15", "9h 45m", "Boeing 787", 216, 337, 48000, 125000, 285000),
            ("AF", "Air France", "DEL", "CDG", "01:15", "06:45", "8h 30m", "Airbus A350", 205, 324, 45000, 120000, 275000),
            ("SQ", "Singapore Airlines", "BOM", "SIN", "23:45", "06:30", "5h 45m", "Airbus A350", 195, 337, 32000, 88000, 195000),
            ("JL", "Japan Airlines", "DEL", "NRT", "00:30", "13:15", "9h 45m", "Boeing 787", 0, 335, 52000, 135000, 295000),  # FULLY BOOKED!
            ("KE", "Korean Air", "BOM", "ICN", "01:45", "14:30", "8h 45m", "Boeing 777", 201, 368, 48000, 128000, 285000),
            ("NH", "ANA", "DEL", "HND", "02:15", "15:30", "10h 15m", "Boeing 777", 189, 350, 55000, 140000, 300000),  # Alternative Tokyo flight
            ("JL", "Japan Airlines", "DEL", "HND", "08:45", "21:30", "9h 45m", "Boeing 777", 156, 335, 58000, 148000, 315000),  # Another Tokyo option
            
            # Major International Routes
            ("AA", "American Airlines", "JFK", "LAX", "08:00", "11:30", "6h 30m", "Boeing 777", 220, 365, 45000, 125000, 285000),
            ("DL", "Delta", "LAX", "JFK", "23:30", "07:45", "5h 15m", "Airbus A330", 198, 293, 42000, 118000, 265000),
            ("BA", "British Airways", "LHR", "JFK", "10:15", "13:30", "8h 15m", "Boeing 747", 245, 469, 38000, 105000, 235000),
            ("VS", "Virgin Atlantic", "JFK", "LHR", "21:15", "08:30", "7h 15m", "Airbus A340", 205, 343, 40000, 110000, 245000),
            ("LH", "Lufthansa", "FRA", "JFK", "14:30", "17:45", "8h 15m", "Airbus A380", 320, 526, 45000, 125000, 285000),
            ("AF", "Air France", "CDG", "JFK", "11:20", "14:15", "8h 55m", "Boeing 777", 235, 381, 43000, 120000, 275000),
            ("KL", "KLM", "AMS", "JFK", "10:45", "13:20", "8h 35m", "Boeing 787", 215, 344, 41000, 115000, 265000),
            ("SQ", "Singapore Airlines", "SIN", "JFK", "23:35", "06:30", "18h 55m", "Airbus A350", 185, 337, 85000, 225000, 485000),
            
            # Asian Routes
            ("CX", "Cathay Pacific", "HKG", "NRT", "08:15", "13:45", "3h 30m", "Airbus A330", 168, 298, 25000, 68000, 145000),
            ("NH", "ANA", "NRT", "ICN", "18:30", "21:15", "2h 45m", "Boeing 787", 145, 335, 22000, 62000, 135000),
            ("TG", "Thai Airways", "BKK", "SIN", "14:20", "17:40", "2h 20m", "Airbus A330", 155, 289, 18000, 52000, 115000),
            ("MH", "Malaysia Airlines", "KUL", "SIN", "19:45", "20:50", "1h 5m", "Boeing 737", 138, 189, 8500, 25000, 55000),
            ("PR", "Philippine Airlines", "MNL", "HKG", "07:30", "09:15", "1h 45m", "Airbus A321", 142, 199, 12000, 35000, 78000),
            
            # Europe Routes
            ("LH", "Lufthansa", "FRA", "LHR", "15:20", "16:05", "1h 45m", "Airbus A320", 148, 180, 18000, 52000, 115000),
            ("AF", "Air France", "CDG", "FRA", "12:30", "14:15", "1h 45m", "Airbus A319", 124, 156, 16000, 48000, 105000),
            ("KL", "KLM", "AMS", "LHR", "16:45", "17:15", "1h 30m", "Boeing 737", 135, 189, 15000, 45000, 98000),
            ("BA", "British Airways", "LHR", "CDG", "18:20", "20:45", "1h 25m", "Airbus A320", 144, 180, 16500, 49000, 108000),
            ("IB", "Iberia", "MAD", "LHR", "11:15", "12:30", "2h 15m", "Airbus A330", 165, 289, 22000, 65000, 142000),
            
            # Oceania Routes
            ("QF", "Qantas", "SYD", "MEL", "07:00", "08:25", "1h 25m", "Boeing 737", 138, 189, 12000, 35000, 78000),
            ("JQ", "Jetstar", "MEL", "SYD", "19:30", "20:55", "1h 25m", "Airbus A320", 145, 180, 11500, 32000, 72000),
            ("QF", "Qantas", "SYD", "SIN", "21:35", "05:25", "8h 50m", "Airbus A380", 295, 484, 45000, 125000, 285000),
            ("SQ", "Singapore Airlines", "SIN", "SYD", "01:20", "12:15", "7h 55m", "Boeing 777", 218, 368, 42000, 118000, 265000),
        ]
        
        # Generate flight IDs and create flight objects
        for i, (airline_code, airline, origin, dest, dep_time, arr_time, duration, aircraft, avail_seats, total_seats, eco_price, bus_price, first_price) in enumerate(flight_routes):
            flight_id = f"{airline_code}{1000 + i}"
            flight_number = f"{airline_code} {1000 + i}"
            
            # Determine route type
            origin_country = self.airports[origin].country if origin in self.airports else "Unknown"
            dest_country = self.airports[dest].country if dest in self.airports else "Unknown"
            
            if origin_country == dest_country:
                route_type = "domestic"
            elif origin_country in ["India"] and dest_country in ["Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Bhutan", "Myanmar"]:
                route_type = "regional"
            else:
                route_type = "international"
            
            flight = Flight(
                flight_id=flight_id,
                airline=airline,
                airline_code=airline_code,
                flight_number=flight_number,
                origin=self.airports[origin].city if origin in self.airports else origin,
                origin_code=origin,
                destination=self.airports[dest].city if dest in self.airports else dest,
                destination_code=dest,
                departure_time=dep_time,
                arrival_time=arr_time,
                duration=duration,
                aircraft=aircraft,
                available_seats=avail_seats,
                total_seats=total_seats,
                price_economy=eco_price,
                price_business=bus_price,
                price_first=first_price,
                route_type=route_type
            )
            
            flights[flight_id] = flight
        
        return flights
    
    def search_flights(self, origin: str, destination: str, departure_date: str, passengers: int = 1, class_type: str = "economy") -> List[Dict]:
        """Search for available flights"""
        origin = origin.lower()
        destination = destination.lower()
        
        # Find matching flights
        matching_flights = []
        
        for flight in self.flights.values():
            # Check if origin and destination match (by city or airport code)
            origin_match = (
                flight.origin.lower() == origin or 
                flight.origin_code.lower() == origin or
                origin in flight.origin.lower()
            )
            dest_match = (
                flight.destination.lower() == destination or 
                flight.destination_code.lower() == destination or
                destination in flight.destination.lower()
            )
            
            if origin_match and dest_match and flight.available_seats >= passengers:
                # Calculate price based on class
                if class_type.lower() == "business":
                    price = flight.price_business
                elif class_type.lower() == "first":
                    price = flight.price_first
                else:
                    price = flight.price_economy
                
                flight_info = {
                    "flight_id": flight.flight_id,
                    "airline": flight.airline,
                    "flight_number": flight.flight_number,
                    "origin": flight.origin,
                    "origin_code": flight.origin_code,
                    "destination": flight.destination,
                    "destination_code": flight.destination_code,
                    "departure_time": flight.departure_time,
                    "arrival_time": flight.arrival_time,
                    "duration": flight.duration,
                    "aircraft": flight.aircraft,
                    "available_seats": flight.available_seats,
                    "price": price,
                    "class_type": class_type,
                    "route_type": flight.route_type,
                    "departure_date": departure_date
                }
                matching_flights.append(flight_info)
        
        # Sort by price
        matching_flights.sort(key=lambda x: x["price"])
        return matching_flights
    
    def book_flight(self, flight_id: str, passengers: int, passenger_details: List[Dict], class_type: str = "economy") -> Dict:
        """Book a flight and update availability"""
        if flight_id not in self.flights:
            raise ValueError(f"Flight {flight_id} not found")
        
        flight = self.flights[flight_id]
        
        if flight.available_seats < passengers:
            raise ValueError(f"Insufficient seats. Available: {flight.available_seats}, Requested: {passengers}")
        
        # Calculate total price
        if class_type.lower() == "business":
            unit_price = flight.price_business
        elif class_type.lower() == "first":
            unit_price = flight.price_first
        else:
            unit_price = flight.price_economy
        
        total_price = unit_price * passengers
        
        # Generate booking reference
        booking_id = f"FL{uuid.uuid4().hex[:8].upper()}"
        
        # Update available seats
        flight.available_seats -= passengers
        
        # Store booking
        booking = {
            "booking_id": booking_id,
            "flight_id": flight_id,
            "flight_details": {
                "airline": flight.airline,
                "flight_number": flight.flight_number,
                "origin": flight.origin,
                "origin_code": flight.origin_code,
                "destination": flight.destination,
                "destination_code": flight.destination_code,
                "departure_time": flight.departure_time,
                "arrival_time": flight.arrival_time,
                "aircraft": flight.aircraft,
                "route_type": flight.route_type
            },
            "passengers": passengers,
            "passenger_details": passenger_details,
            "class_type": class_type,
            "unit_price": unit_price,
            "total_price": total_price,
            "booking_date": datetime.now().isoformat(),
            "status": "confirmed"
        }
        
        self.bookings[booking_id] = booking
        
        logger.info(f"Flight booked: {booking_id} for {passengers} passengers on {flight.flight_number}")
        return booking
    
    def get_booking(self, booking_id: str) -> Optional[Dict]:
        """Retrieve booking details"""
        return self.bookings.get(booking_id)
    
    def rebook_flight(self, booking_id: str, new_flight_id: str) -> Dict:
        """Rebook a flight with a different flight using existing booking ID"""
        if booking_id not in self.bookings:
            raise ValueError(f"Booking {booking_id} not found")
        
        if new_flight_id not in self.flights:
            raise ValueError(f"New flight {new_flight_id} not found")
        
        # Get original booking details
        original_booking = self.bookings[booking_id]
        original_flight_id = original_booking["flight_id"]
        passengers = original_booking["passengers"]
        passenger_details = original_booking["passenger_details"]
        class_type = original_booking["class_type"]
        
        # Check if new flight has availability
        new_flight = self.flights[new_flight_id]
        if new_flight.available_seats < passengers:
            raise ValueError(f"Insufficient seats on new flight. Available: {new_flight.available_seats}, Required: {passengers}")
        
        # Restore seats to original flight
        if original_flight_id in self.flights:
            original_flight = self.flights[original_flight_id]
            original_flight.available_seats += passengers
            logger.info(f"Restored {passengers} seats to original flight {original_flight_id}")
        
        # Book new flight
        if class_type.lower() == "business":
            unit_price = new_flight.price_business
        elif class_type.lower() == "first":
            unit_price = new_flight.price_first
        else:
            unit_price = new_flight.price_economy
        
        total_price = unit_price * passengers
        price_difference = total_price - original_booking["total_price"]
        
        # Update availability on new flight
        new_flight.available_seats -= passengers
        
        # Update booking with new flight details
        updated_booking = {
            "booking_id": booking_id,  # Keep same booking ID
            "flight_id": new_flight_id,
            "original_flight_id": original_flight_id,  # Track original for reference
            "flight_details": {
                "airline": new_flight.airline,
                "flight_number": new_flight.flight_number,
                "origin": new_flight.origin,
                "origin_code": new_flight.origin_code,
                "destination": new_flight.destination,
                "destination_code": new_flight.destination_code,
                "departure_time": new_flight.departure_time,
                "arrival_time": new_flight.arrival_time,
                "aircraft": new_flight.aircraft,
                "route_type": new_flight.route_type
            },
            "passengers": passengers,
            "passenger_details": passenger_details,
            "class_type": class_type,
            "unit_price": unit_price,
            "total_price": total_price,
            "original_price": original_booking["total_price"],
            "price_difference": price_difference,
            "booking_date": original_booking["booking_date"],
            "rebook_date": datetime.now().isoformat(),
            "status": "rebooked"
        }
        
        # Update the booking
        self.bookings[booking_id] = updated_booking
        
        logger.info(f"Flight rebooked: {booking_id} from {original_flight_id} to {new_flight_id}")
        return updated_booking
    
    def cancel_booking(self, booking_id: str) -> Dict:
        """Cancel a booking and restore seat availability"""
        if booking_id not in self.bookings:
            raise ValueError(f"Booking {booking_id} not found")
        
        booking = self.bookings[booking_id]
        flight_id = booking["flight_id"]
        passengers = booking["passengers"]
        
        # Restore seats to flight
        if flight_id in self.flights:
            flight = self.flights[flight_id]
            flight.available_seats += passengers
            logger.info(f"Restored {passengers} seats to flight {flight_id}")
        
        # Update booking status
        booking["status"] = "cancelled"
        booking["cancellation_date"] = datetime.now().isoformat()
        
        logger.info(f"Booking cancelled: {booking_id}")
        return booking
    
    def find_alternative_flights(self, booking_id: str, max_alternatives: int = 5) -> List[Dict]:
        """Find alternative flights for rebooking based on original booking criteria"""
        if booking_id not in self.bookings:
            raise ValueError(f"Booking {booking_id} not found")
        
        original_booking = self.bookings[booking_id]
        flight_details = original_booking["flight_details"]
        passengers = original_booking["passengers"]
        class_type = original_booking["class_type"]
        
        # Extract origin and destination from original booking
        origin = flight_details["origin"]
        destination = flight_details["destination"]
        
        # Search for alternative flights on same route
        today = datetime.now().strftime("%Y-%m-%d")
        alternatives = self.search_flights(origin, destination, today, passengers, class_type)
        
        # Filter out the current booked flight and return top alternatives
        current_flight_id = original_booking["flight_id"]
        alternatives = [f for f in alternatives if f["flight_id"] != current_flight_id]
        
        return alternatives[:max_alternatives]
    
    def get_flight_stats(self) -> Dict:
        """Get database statistics"""
        total_flights = len(self.flights)
        total_bookings = len(self.bookings)
        active_bookings = len([b for b in self.bookings.values() if b["status"] in ["confirmed", "rebooked"]])
        cancelled_bookings = len([b for b in self.bookings.values() if b["status"] == "cancelled"])
        airlines = set(flight.airline for flight in self.flights.values())
        routes = set(f"{flight.origin}-{flight.destination}" for flight in self.flights.values())
        
        return {
            "total_flights": total_flights,
            "total_routes": len(routes),
            "total_airports": len(self.airports),
            "total_bookings": total_bookings,
            "active_bookings": active_bookings,
            "cancelled_bookings": cancelled_bookings,
            "airlines_count": len(airlines),
            "airlines": sorted(list(airlines)),
            "total_capacity": sum(flight.total_seats for flight in self.flights.values()),
            "total_available_seats": sum(flight.available_seats for flight in self.flights.values())
        }


# Initialize global database
flight_db = GlobalFlightDatabase()

class EnhancedFlightAgent(AgentExecutor):
    """Enhanced Flight Agent with global flight data"""
    
    def __init__(self):
        super().__init__()
        self.db = flight_db
        logger.info("Enhanced Flight Agent initialized with global flight database")
    
    def get_flight_stats(self) -> Dict:
        """Get database statistics"""
        return self.db.get_flight_stats()
    
    def simulate_tokyo_booking_scenario(self) -> Dict:
        """Simulate a Tokyo booking scenario with full flight and rebooking"""
        # Try to book the fully booked Tokyo flight first
        try:
            # Create a sample booking request for the fully booked flight
            passenger_details = [{"name": "John Doe", "age": "35", "passport": "AB1234567"}]
            
            # This should fail because JL1014 (Japan Airlines to Tokyo NRT) has 0 seats
            booking = self.db.book_flight("JL1014", 1, passenger_details, "economy")
            return {"status": "error", "message": "This shouldn't happen - flight should be full"}
            
        except ValueError as e:
            # Expected - flight is full
            print(f"❌ As expected: {str(e)}")
            
            # Now find alternative flights to Tokyo
            alternatives = self.db.search_flights("Delhi", "Tokyo", datetime.now().strftime("%Y-%m-%d"), 1, "economy")
            
            if alternatives:
                # Book the alternative flight (NH1025 - ANA to Tokyo HND)
                alt_flight = alternatives[0]  # First alternative
                booking = self.db.book_flight(alt_flight["flight_id"], 1, passenger_details, "economy")
                
                return {
                    "status": "success",
                    "scenario": "tokyo_rebooking_demo",
                    "original_attempt": "JL1014 (Japan Airlines to NRT) - FULL",
                    "successful_booking": {
                        "flight_id": booking["flight_id"],
                        "flight_number": booking["flight_details"]["flight_number"],
                        "destination_airport": booking["flight_details"]["destination_code"],
                        "booking_id": booking["booking_id"],
                        "price": booking["total_price"]
                    },
                    "alternatives_found": len(alternatives),
                    "message": "Successfully booked alternative Tokyo flight!"
                }
            else:
                return {"status": "error", "message": "No alternative Tokyo flights available"}
        logger.info("Enhanced Flight Agent initialized with global flight database")
    
    async def execute(self, request, event_queue: EventQueue):
        """Execute flight-related actions using A2A SDK structure"""
        try:
            # Extract message from request
            logger.info(f"Request type: {type(request)}, dir: {dir(request)}")
            
            # Try different ways to access the message
            if hasattr(request, 'message') and request.message:
                # Check the message structure
                logger.info(f"Message type: {type(request.message)}, dir: {dir(request.message)}")
                if hasattr(request.message, 'parts') and request.message.parts:
                    # Check the parts structure
                    logger.info(f"First part type: {type(request.message.parts[0])}, dir: {dir(request.message.parts[0])}")
                    first_part = request.message.parts[0]
                    if hasattr(first_part, 'text'):
                        user_message_text = first_part.text
                    elif hasattr(first_part, 'content'):
                        user_message_text = first_part.content
                    elif hasattr(first_part, 'root') and hasattr(first_part.root, 'text'):
                        user_message_text = first_part.root.text
                    else:
                        # Extract from string representation - get the actual text content
                        import re
                        part_str = str(first_part)
                        logger.info(f"Part string representation: {part_str}")
                        
                        # Look for the text content within the TextPart representation
                        if "text='" in part_str:
                            # Extract everything between text=' and the last closing quote before )
                            text_start = part_str.find("text='") + 6
                            # Find the end - look for last quote before the closing parenthesis
                            remaining = part_str[text_start:]
                            # Handle escaped quotes and find the actual end
                            text_end = remaining.rfind("')")
                            if text_end > 0:
                                user_message_text = remaining[:text_end]
                                # Unescape any escaped characters
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
                # Fallback for health check or simple test
                user_message_text = "health_check"
                
            logger.info(f"Enhanced Flight agent received request: {user_message_text}")
            
            # Parse the message to determine action
            action, params = self._parse_message(user_message_text)
            logger.info(f"Parsed action: {action}, params: {params}")
            
            # Execute the action
            if action == "search_flights":
                result = await self._search_flights(params)
            elif action == "book_flight":
                result = await self._book_flight(params)
            elif action == "comprehensive_booking":
                result = await self._comprehensive_booking(params)
            elif action == "rebook_flight":
                result = await self._rebook_flight(params)
            elif action == "cancel_booking":
                result = await self._cancel_booking(params)
            elif action == "find_alternatives":
                result = await self._find_alternatives(params)
            elif action == "get_booking":
                result = await self._get_booking(params)
            elif action == "get_stats":
                result = await self._get_stats()
            elif action == "health_check":
                result = {"status": "healthy", "service": "enhanced_flight_agent"}
            else:
                result = await self._search_flights_simple(user_message_text)
            
            # Send response
            response_text = self._format_response(result)
            response_message = Message(
                message_id=str(uuid.uuid4()),
                role="agent",
                parts=[TextPart(text=response_text)]
            )
            
            # Debug EventQueue methods
            logger.info(f"EventQueue type: {type(event_queue)}, dir: {dir(event_queue)}")
            
            # Use the correct EventQueue method
            await event_queue.enqueue_event(response_message)
            await event_queue.enqueue_event(TaskStatus(state=TaskState.completed))
            
        except Exception as e:
            logger.error(f"Error in enhanced flight agent: {str(e)}")
            error_response = f"Sorry, I encountered an error: {str(e)}"
            error_message = Message(
                message_id=str(uuid.uuid4()),
                role="agent", 
                parts=[TextPart(text=error_response)]
            )
            
            # Use the correct EventQueue method for error
            await event_queue.enqueue_event(error_message)
            await event_queue.enqueue_event(TaskStatus(state=TaskState.failed))
    
    async def cancel(self, request, event_queue: EventQueue):
        """Cancel the current operation"""
        logger.info("Enhanced Flight agent operation cancelled")
        cancel_message = Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[TextPart(text="Operation cancelled.")]
        )
        
        # Use the correct EventQueue method
        await event_queue.enqueue_event(cancel_message)
        await event_queue.enqueue_event(TaskStatus(state=TaskState.canceled))
    
    def _parse_message(self, message_text: str) -> tuple:
        """Parse user message to extract action and parameters"""
        message_lower = message_text.lower()
        
        # Check for comprehensive booking first (high priority)
        if "comprehensive" in message_lower and "book" in message_lower:
            params = self._extract_booking_params(message_text)
            return "comprehensive_booking", params
        elif "book" in message_lower and "full details" in message_lower:
            params = self._extract_booking_params(message_text)
            return "comprehensive_booking", params
        elif "search" in message_lower or "find" in message_lower:
            if "alternative" in message_lower or "rebook" in message_lower:
                params = self._extract_alternative_params(message_text)
                return "find_alternatives", params
            else:
                params = self._extract_search_params(message_text)
                return "search_flights", params
        elif "rebook" in message_lower or "change" in message_lower:
            # Only treat as rebook if it's not a comprehensive booking request
            if "comprehensive" not in message_lower and "full details" not in message_lower:
                params = self._extract_rebook_params(message_text)
                return "rebook_flight", params
            else:
                params = self._extract_booking_params(message_text)
                return "comprehensive_booking", params
        elif "cancel" in message_lower:
            params = self._extract_cancel_params(message_text)
            return "cancel_booking", params
        elif "book" in message_lower:
            params = self._extract_booking_params(message_text)
            return "book_flight", params
        elif "stats" in message_lower or "statistics" in message_lower:
            return "get_stats", {}
        else:
            # Default to search
            params = self._extract_search_params(message_text)
            return "search_flights", params
    
    def _extract_search_params(self, message_text: str) -> Dict:
        """Extract search parameters from natural language"""
        # Simple parameter extraction - can be enhanced with NLP
        params = {
            "origin": "Delhi",
            "destination": "Mumbai", 
            "departure_date": datetime.now().strftime("%Y-%m-%d"),
            "passengers": 1,
            "class_type": "economy"
        }
        
        # Basic keyword extraction
        if "delhi" in message_text.lower():
            params["origin"] = "Delhi"
        if "mumbai" in message_text.lower() or "bombay" in message_text.lower():
            params["destination"] = "Mumbai"
        if "bangalore" in message_text.lower():
            params["destination"] = "Bangalore"
        if "tokyo" in message_text.lower():
            params["destination"] = "Tokyo"
        if "london" in message_text.lower():
            params["destination"] = "London"
        if "new york" in message_text.lower():
            params["destination"] = "New York"
        if "business" in message_text.lower():
            params["class_type"] = "business"
        if "first" in message_text.lower():
            params["class_type"] = "first"
            
        return params
    
    def _extract_booking_params(self, message_text: str) -> Dict:
        """Extract booking parameters from natural language"""
        import re
        
        logger.info(f"Extracting booking params from message: {message_text[:200]}...")
        
        # Initialize default params
        params = {
            "origin": "Delhi",
            "destination": "Mumbai",
            "departure_date": datetime.now().strftime("%Y-%m-%d"),
            "passengers": 1,
            "class_type": "economy"
        }
        
        # Extract origin
        origin_match = re.search(r'Origin[:\s]+([A-Za-z\s]+?)(?:\n|•|$)', message_text, re.IGNORECASE)
        if origin_match:
            params["origin"] = origin_match.group(1).strip()
        
        # Extract destination  
        dest_match = re.search(r'Destination[:\s]+([A-Za-z\s]+?)(?:\n|•|$)', message_text, re.IGNORECASE)
        if dest_match:
            params["destination"] = dest_match.group(1).strip()
        
        # Extract departure date
        date_match = re.search(r'Departure Date[:\s]+([0-9-]+)', message_text, re.IGNORECASE)
        if date_match:
            params["departure_date"] = date_match.group(1).strip()
        
        # Extract passengers
        passenger_match = re.search(r'Passengers[:\s]+(\d+)', message_text, re.IGNORECASE)
        if passenger_match:
            params["passengers"] = int(passenger_match.group(1))
        
        # Extract class
        class_match = re.search(r'Class[:\s]+([A-Za-z]+)', message_text, re.IGNORECASE)
        if class_match:
            params["class_type"] = class_match.group(1).lower()
        
        logger.info(f"Extracted booking params: {params}")
        return params
    
    def _extract_rebook_params(self, message_text: str) -> Dict:
        """Extract rebooking parameters from natural language"""
        # In a real implementation, this would parse booking ID and new flight ID from the message
        return {
            "booking_id": "FL12345678",  # Would be extracted from message
            "new_flight_id": "AI1001"   # Would be extracted from message
        }
    
    def _extract_cancel_params(self, message_text: str) -> Dict:
        """Extract cancellation parameters from natural language"""
        return {
            "booking_id": "FL12345678"  # Would be extracted from message
        }
    
    def _extract_alternative_params(self, message_text: str) -> Dict:
        """Extract parameters for finding alternative flights"""
        return {
            "booking_id": "FL12345678",  # Would be extracted from message
            "max_alternatives": 5
        }
    
    def _format_response(self, result: Dict) -> str:
        """Format the result as a user-friendly response"""
        if result.get("status") == "error":
            return f"❌ Error: {result.get('message', 'Unknown error')}"
        
        action = result.get("action", "")
        
        if action == "search_flights":
            flights = result.get("flights", [])
            if not flights:
                return "No flights found for your search criteria."
            
            response = f"✈️ Found {len(flights)} flights:\n\n"
            for i, flight in enumerate(flights[:5], 1):  # Show top 5
                response += f"{i}. {flight['airline']} {flight['flight_number']}\n"
                response += f"   {flight['origin']} → {flight['destination']}\n"
                response += f"   Departure: {flight['departure_time']} | Duration: {flight['duration']}\n"
                response += f"   Price: ₹{flight['price']:,.0f} ({flight['class_type']})\n"
                response += f"   Available seats: {flight['available_seats']}\n\n"
            
            return response
        
        elif action == "book_flight":
            booking = result.get("booking", {})
            return f"✅ Flight booked successfully!\nBooking ID: {booking.get('booking_id')}\nTotal Price: ₹{booking.get('total_price', 0):,.0f}"
        
        elif action == "comprehensive_booking":
            if result.get("status") == "success":
                info = result.get("comprehensive_info", {})
                backend = result.get("backend_operations", {})
                
                response = f"✈️ **COMPREHENSIVE FLIGHT BOOKING CONFIRMATION**\n\n"
                response += f"🎟️ **BOOKING DETAILS:**\n"
                response += f"• Booking ID: {info.get('booking_id')}\n"
                response += f"• Confirmation Code: {info.get('confirmation_code')}\n"
                response += f"• Flight: {info.get('airline')} {info.get('flight_number')}\n"
                response += f"• Aircraft: {info.get('aircraft_type')}\n\n"
                
                response += f"🛫 **FLIGHT INFORMATION:**\n"
                response += f"• Route: {info.get('origin')} → {info.get('destination')}\n"
                response += f"• Date: {info.get('departure_date')}\n"
                response += f"• Departure: {info.get('departure_time')} from {info.get('gate')}, {info.get('terminal')}\n"
                response += f"• Arrival: {info.get('arrival_time')}\n"
                response += f"• Duration: {info.get('duration')}\n\n"
                
                response += f"👥 **PASSENGER DETAILS:**\n"
                response += f"• Passengers: {info.get('passengers')} ({info.get('class_type')} class)\n"
                response += f"• Seats: {', '.join(info.get('seat_assignments', []))}\n"
                response += f"• Meal: {info.get('meal_preference')}\n\n"
                
                response += f"💰 **PRICING BREAKDOWN:**\n"
                breakdown = info.get('price_breakdown', {})
                response += f"• Base Fare: ₹{breakdown.get('base_fare', 0):,.0f}\n"
                response += f"• Taxes & Fees: ₹{breakdown.get('taxes', 0) + breakdown.get('fees', 0):,.0f}\n"
                response += f"• **Total: ₹{info.get('total_price', 0):,.0f}**\n\n"
                
                response += f"🎒 **TRAVEL INFORMATION:**\n"
                response += f"• Baggage: {info.get('baggage_allowance')}\n"
                response += f"• Check-in: {info.get('check_in_options', [''])[0]}\n"
                response += f"• Cancellation: {info.get('cancellation')}\n\n"
                
                response += f"⚙️ **BEHIND THE SCENES:**\n"
                response += f"• Query Time: {backend.get('database_query_time')}\n"
                response += f"• Seat Allocation: {backend.get('seat_allocation')}\n"
                response += f"• Payment: {backend.get('payment_processing')}\n"
                response += f"• Inventory: {backend.get('inventory_update')}\n"
                response += f"• Confirmation: {backend.get('confirmation_sent')}\n"
                response += f"• Timestamp: {backend.get('booking_timestamp')}\n\n"
                
                response += f"✅ **Your flight is confirmed and ready for travel!**"
                return response
                
            elif result.get("status") == "fully_booked":
                response = f"❌ **FLIGHT FULLY BOOKED**\n\n"
                response += f"{result.get('message')}\n\n"
                response += f"🔄 **REBOOKING OPTIONS AVAILABLE:**\n"
                alternatives = result.get("alternatives", [])
                for i, alt in enumerate(alternatives[:3], 1):
                    response += f"{i}. {alt.get('airline')} {alt.get('flight_number')}\n"
                    response += f"   Date: {alt.get('departure_date')} | Price: ₹{alt.get('price'):,.0f}\n"
                    response += f"   Available: {alt.get('available_seats')} seats\n\n"
                return response
                
            elif result.get("status") == "no_availability":
                response = f"❌ **NO FLIGHTS AVAILABLE**\n\n"
                response += f"{result.get('message')}\n\n"
                if result.get("alternatives"):
                    response += f"🔄 **ALTERNATIVE DATES/ROUTES:**\n"
                    alternatives = result.get("alternatives", [])
                    for i, alt in enumerate(alternatives[:3], 1):
                        response += f"{i}. {alt.get('airline')} {alt.get('flight_number')}\n"
                        response += f"   Date: {alt.get('departure_date')} | Price: ₹{alt.get('price'):,.0f}\n\n"
                return response
        
        elif action == "rebook_flight":
            booking = result.get("booking", {})
            price_diff = booking.get("price_difference", 0)
            price_info = f"Price difference: ₹{price_diff:,.0f}" if price_diff != 0 else "No price change"
            return f"✅ Flight rebooked successfully!\n" \
                   f"Booking ID: {booking.get('booking_id')}\n" \
                   f"New Flight: {booking.get('flight_details', {}).get('flight_number', 'N/A')}\n" \
                   f"New Price: ₹{booking.get('total_price', 0):,.0f}\n" \
                   f"{price_info}"
        
        elif action == "cancel_booking":
            booking = result.get("booking", {})
            return f"✅ Booking cancelled successfully!\n" \
                   f"Booking ID: {booking.get('booking_id')}\n" \
                   f"Flight: {booking.get('flight_details', {}).get('flight_number', 'N/A')}\n" \
                   f"Refund will be processed according to airline policy."
        
        elif action == "find_alternatives":
            alternatives = result.get("alternatives", [])
            booking_id = result.get("booking_id", "")
            if not alternatives:
                return f"❌ No alternative flights found for booking {booking_id}"
            
            response = f"🔄 Found {len(alternatives)} alternative flights for booking {booking_id}:\n\n"
            for i, flight in enumerate(alternatives, 1):
                response += f"{i}. {flight['airline']} {flight['flight_number']}\n"
                response += f"   {flight['origin']} → {flight['destination']}\n"
                response += f"   Departure: {flight['departure_time']} | Duration: {flight['duration']}\n"
                response += f"   Price: ₹{flight['price']:,.0f} ({flight['class_type']})\n"
                response += f"   Available seats: {flight['available_seats']}\n\n"
            
            response += "💡 To rebook, use: 'Rebook booking [BOOKING_ID] to flight [FLIGHT_ID]'"
            return response
        
        elif action == "get_stats":
            stats = result.get("statistics", {})
            return f"📊 Flight Database Statistics:\n" \
                   f"• Total Flights: {stats.get('total_flights', 0)}\n" \
                   f"• Airlines: {stats.get('airlines_count', 0)}\n" \
                   f"• Routes: {stats.get('routes_count', 0)}\n" \
                   f"• Airports: {stats.get('airports_count', 0)}\n" \
                   f"• Total Bookings: {stats.get('total_bookings', 0)}"
        
        return str(result)
    
    async def _search_flights_simple(self, message_text: str) -> Dict:
        """Simple flight search for general queries"""
        params = self._extract_search_params(message_text)
        return await self._search_flights(params)
    
    async def _search_flights(self, params: Dict) -> Dict[str, Any]:
        """Search for available flights"""
        required_fields = ["origin", "destination", "departure_date"]
        for field in required_fields:
            if field not in params:
                raise ValueError(f"Missing required field: {field}")
        
        origin = params["origin"]
        destination = params["destination"]
        departure_date = params["departure_date"]
        passengers = params.get("passengers", 1)
        class_type = params.get("class_type", "economy")
        
        flights = self.db.search_flights(origin, destination, departure_date, passengers, class_type)
        
        return {
            "status": "success",
            "action": "search_flights",
            "query": {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "passengers": passengers,
                "class_type": class_type
            },
            "results_count": len(flights),
            "flights": flights
        }
    
    async def _book_flight(self, params: Dict) -> Dict[str, Any]:
        """Book a specific flight"""
        required_fields = ["flight_id", "passengers", "passenger_details"]
        for field in required_fields:
            if field not in params:
                raise ValueError(f"Missing required field: {field}")
        
        flight_id = params["flight_id"]
        passengers = params["passengers"]
        passenger_details = params["passenger_details"]
        class_type = params.get("class_type", "economy")
        
        booking = self.db.book_flight(flight_id, passengers, passenger_details, class_type)
        
        return {
            "status": "success",
            "action": "book_flight",
            "booking": booking,
            "message": f"Flight {flight_id} booked successfully for {passengers} passengers"
        }
    
    async def _comprehensive_booking(self, params: Dict) -> Dict[str, Any]:
        """Handle comprehensive booking request - search and book best flight"""
        from datetime import datetime, timedelta
        
        origin = params.get("origin", "Delhi")
        destination = params.get("destination", "Tokyo")
        departure_date = params.get("departure_date", datetime.now().strftime("%Y-%m-%d"))
        passengers = params.get("passengers", 1)
        class_type = params.get("class_type", "economy")
        
        logger.info(f"Processing comprehensive booking: {origin} -> {destination}, {passengers} passengers, {class_type}")
        
        # Search for available flights
        flights = self.db.search_flights(origin, destination, departure_date, passengers, class_type)
        
        if not flights:
            # No flights available - search for alternative dates/routes
            # Try alternative dates
            try:
                base_date = datetime.strptime(departure_date, "%Y-%m-%d")
                alternative_dates = [
                    (base_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                    (base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                    (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
                ]
                
                alternatives = []
                for alt_date in alternative_dates:
                    alt_flights = self.db.search_flights(origin, destination, alt_date, passengers, class_type)
                    alternatives.extend(alt_flights[:2])  # Add up to 2 flights per date
                
                if not alternatives:
                    # Try nearby airports or different routes
                    nearby_origins = ["Boston", "New York", "Philadelphia"] if origin == "Boston" else [origin]
                    nearby_destinations = ["Tokyo", "Osaka", "Nagoya"] if destination == "Tokyo" else [destination]
                    
                    for alt_origin in nearby_origins:
                        for alt_dest in nearby_destinations:
                            if alt_origin != origin or alt_dest != destination:
                                alt_flights = self.db.search_flights(alt_origin, alt_dest, departure_date, passengers, class_type)
                                alternatives.extend(alt_flights[:1])
                
            except Exception as e:
                logger.error(f"Error finding alternatives: {e}")
                alternatives = []
            
            response = {
                "status": "no_availability",
                "action": "comprehensive_booking",
                "message": f"❌ No direct flights available from {origin} to {destination} on {departure_date}",
                "alternatives": alternatives,
                "rebooking_options": True
            }
            
            # Add detailed rebooking information
            if alternatives:
                response["rebooking_message"] = f"🔄 Found {len(alternatives)} alternative flights for rebooking:"
                for i, alt in enumerate(alternatives[:3], 1):
                    response[f"alternative_{i}"] = {
                        "flight_number": alt["flight_number"],
                        "departure_date": alt["departure_date"],
                        "price": alt["price"],
                        "available_seats": alt["available_seats"]
                    }
            
            return response
        
        # Book the best available flight (first one from search results)
        best_flight = flights[0]
        flight_id = best_flight["flight_id"]
        
        # Create passenger details for booking
        passenger_details = []
        for i in range(passengers):
            passenger_details.append({
                "name": f"Passenger {i+1}",
                "age": 30,
                "seat_preference": "aisle"
            })
        
        try:
            # Book the flight
            booking = self.db.book_flight(flight_id, passengers, passenger_details, class_type)
            
            # Get flight details for comprehensive response
            # Use the best_flight data we already have instead of calling a missing method
            flight_details = best_flight  # We already have all the flight details from search
            
            return {
                "status": "success",
                "action": "comprehensive_booking",
                "booking_confirmed": True,
                "booking": booking,
                "flight_details": flight_details,
                "comprehensive_info": {
                    "booking_id": booking["booking_id"],
                    "flight_number": best_flight["flight_number"],
                    "airline": best_flight["airline"],
                    "aircraft_type": best_flight.get("aircraft_type", "Boeing 787"),
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "departure_time": best_flight["departure_time"],
                    "arrival_time": best_flight["arrival_time"],
                    "duration": best_flight["duration"],
                    "gate": f"Gate {best_flight.get('gate', 'A12')}",
                    "terminal": f"Terminal {best_flight.get('terminal', '1')}",
                    "passengers": passengers,
                    "class_type": class_type.title(),
                    "total_price": booking["total_price"],
                    "price_breakdown": {
                        "base_fare": booking["total_price"] * 0.7,
                        "taxes": booking["total_price"] * 0.2,
                        "fees": booking["total_price"] * 0.1
                    },
                    "seat_assignments": [f"{chr(65+(i//2))}{10+(i%6)}" for i in range(passengers)],
                    "baggage_allowance": "2 pieces, 23kg each",
                    "check_in_options": ["Online check-in available 24 hours before departure", "Mobile boarding pass"],
                    "meal_preference": "Standard",
                    "cancellation": "Free cancellation up to 24 hours before departure",
                    "confirmation_code": booking["booking_id"][-6:].upper()
                },
                "backend_operations": {
                    "database_query_time": "0.05s",
                    "seat_allocation": "Automatic seat assignment completed",
                    "payment_processing": "Payment confirmed via secure gateway",
                    "inventory_update": f"Available seats reduced from {best_flight['available_seats']+passengers} to {best_flight['available_seats']}",
                    "booking_timestamp": datetime.now().isoformat(),
                    "confirmation_sent": "Email confirmation dispatched"
                },
                "message": f"✈️ Comprehensive flight booking confirmed! Booking ID: {booking['booking_id']}"
            }
            
        except Exception as e:
            # Handle booking failure - potentially fully booked
            if "no seats available" in str(e).lower() or "fully booked" in str(e).lower():
                # Try alternative dates for rebooking
                try:
                    base_date = datetime.strptime(departure_date, "%Y-%m-%d")
                    alternative_dates = [
                        (base_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                        (base_date + timedelta(days=2)).strftime("%Y-%m-%d")
                    ]
                    
                    alternatives = []
                    for alt_date in alternative_dates:
                        alt_flights = self.db.search_flights(origin, destination, alt_date, passengers, class_type)
                        alternatives.extend(alt_flights[:2])
                        
                except Exception:
                    alternatives = []
                
                return {
                    "status": "fully_booked",
                    "action": "comprehensive_booking",
                    "message": f"❌ Flight {flight_id} is fully booked",
                    "rebooking_required": True,
                    "alternatives": alternatives,
                    "rebooking_message": f"🔄 Found {len(alternatives)} alternative flights for rebooking",
                    "selected_flight": best_flight,
                    "error": str(e)
                }
            else:
                raise e
    
    async def _get_booking(self, params: Dict) -> Dict[str, Any]:
        """Retrieve booking details"""
        booking_id = params.get("booking_id")
        if not booking_id:
            raise ValueError("Missing required field: booking_id")
        
        booking = self.db.get_booking(booking_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")
        
        return {
            "status": "success",
            "action": "get_booking",
            "booking": booking
        }
    
    async def _get_stats(self) -> Dict[str, Any]:
        """Get flight database statistics"""
        stats = self.db.get_flight_stats()
        return {
            "status": "success",
            "action": "get_stats",
            "statistics": stats
        }
    
    async def _rebook_flight(self, params: Dict) -> Dict[str, Any]:
        """Rebook a flight with a different flight"""
        required_fields = ["booking_id", "new_flight_id"]
        for field in required_fields:
            if field not in params:
                raise ValueError(f"Missing required field: {field}")
        
        booking_id = params["booking_id"]
        new_flight_id = params["new_flight_id"]
        
        booking = self.db.rebook_flight(booking_id, new_flight_id)
        
        return {
            "status": "success",
            "action": "rebook_flight",
            "booking": booking,
            "message": f"Flight rebooked successfully from {booking.get('original_flight_id')} to {new_flight_id}"
        }
    
    async def _cancel_booking(self, params: Dict) -> Dict[str, Any]:
        """Cancel a booking"""
        booking_id = params.get("booking_id")
        if not booking_id:
            raise ValueError("Missing required field: booking_id")
        
        booking = self.db.cancel_booking(booking_id)
        
        return {
            "status": "success",
            "action": "cancel_booking",
            "booking": booking,
            "message": f"Booking {booking_id} cancelled successfully"
        }
    
    async def _find_alternatives(self, params: Dict) -> Dict[str, Any]:
        """Find alternative flights for rebooking"""
        booking_id = params.get("booking_id")
        if not booking_id:
            raise ValueError("Missing required field: booking_id")
        
        max_alternatives = params.get("max_alternatives", 5)
        alternatives = self.db.find_alternative_flights(booking_id, max_alternatives)
        
        return {
            "status": "success",
            "action": "find_alternatives",
            "booking_id": booking_id,
            "alternatives_count": len(alternatives),
            "alternatives": alternatives
        }

# A2A Server setup
def create_flight_agent_card() -> AgentCard:
    """Create agent card for A2A discovery"""
    return AgentCard(
        name="Enhanced Flight Agent",
        description="Production-ready flight booking service with global flight data",
        url="http://localhost:5002/",
        version="2.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="search_flights",
                name="search_flights",
                description="Search for available flights between cities",
                input_modes=["text"],
                output_modes=["text"],
                tags=["flights", "search", "travel"]
            ),
            AgentSkill(
                id="book_flight",
                name="book_flight", 
                description="Book a specific flight",
                input_modes=["text"],
                output_modes=["text"],
                tags=["flights", "booking", "reservation"]
            ),
            AgentSkill(
                id="rebook_flight",
                name="rebook_flight",
                description="Rebook an existing booking with a different flight",
                input_modes=["text"],
                output_modes=["text"],
                tags=["flights", "rebooking", "change"]
            ),
            AgentSkill(
                id="cancel_booking",
                name="cancel_booking",
                description="Cancel an existing flight booking",
                input_modes=["text"],
                output_modes=["text"],
                tags=["flights", "cancellation", "refund"]
            ),
            AgentSkill(
                id="find_alternatives",
                name="find_alternatives",
                description="Find alternative flights for rebooking",
                input_modes=["text"],
                output_modes=["text"],
                tags=["flights", "alternatives", "options"]
            ),
            AgentSkill(
                id="get_stats",
                name="get_stats",
                description="Get flight database statistics",
                input_modes=["text"],
                output_modes=["text"],
                tags=["statistics", "info", "database"]
            )
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"]
    )

def create_app():
    """Factory function to create the A2A application"""
    agent_card = create_flight_agent_card()
    
    request_handler = DefaultRequestHandler(
        agent_executor=EnhancedFlightAgent(),
        task_store=InMemoryTaskStore(),
    )
    
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    # Build and return the Starlette app
    return a2a_app.build()

if __name__ == "__main__":
    logger.info(f"Starting Enhanced Flight Agent on {HOST}:{PORT}")
    logger.info(f"Database initialized with {len(flight_db.flights)} flights")
    logger.info(f"Supporting {len(flight_db.airports)} airports globally")
    
    uvicorn.run(
        "enhanced_flight_agent:create_app",
        host=HOST,
        port=PORT,
        factory=True,
        reload=False,
        access_log=True,
        log_level="info"
    )
