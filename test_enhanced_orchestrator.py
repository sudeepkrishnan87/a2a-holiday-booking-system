#!/usr/bin/env python3
"""
Test script to demonstrate enhanced orchestrator flight booking functionality.
This script tests the comprehensive flight ticket status display.
"""

import requests
import json
import time

def test_comprehensive_flight_booking():
    """Test comprehensive flight booking with detailed ticket status."""
    
    # Orchestrator endpoint
    orchestrator_url = "http://localhost:9001/book-holiday"
    
    # Test booking request - using Delhi to Mumbai route (should have availability)
    booking_request = {
        "destination": "Mumbai",
        "departure_city": "Delhi", 
        "departure_date": "2025-08-15",
        "return_date": "2025-08-20",
        "passengers": 2,
        "budget": 50000,
        "preferences": {
            "flight_class": "Economy",
            "hotel_rating": 4,
            "transport": "Cab"
        }
    }
    
    print("🧪 Testing Enhanced Orchestrator Flight Booking")
    print("=" * 60)
    print(f"📅 Request: {json.dumps(booking_request, indent=2)}")
    print("=" * 60)
    
    try:
        # Send booking request
        print("📤 Sending booking request to orchestrator...")
        response = requests.post(orchestrator_url, json=booking_request, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Booking request successful!")
            print("\n🎫 DETAILED FLIGHT TICKET STATUS:")
            print("=" * 60)
            
            # Display the comprehensive flight details
            if 'results' in result:
                for service_result in result['results']:
                    if service_result['service'] == 'flight':
                        print(f"📋 Service: {service_result['service'].upper()}")
                        print(f"📊 Status: {service_result['status']}")
                        print("\n📝 COMPREHENSIVE FLIGHT DETAILS:")
                        print("-" * 40)
                        print(service_result['message'])
                        print("-" * 40)
                        
                        if 'booking_details' in service_result:
                            print(f"\n🔧 Backend Details:")
                            details = service_result['booking_details']
                            for key, value in details.items():
                                if key not in ['message']:
                                    print(f"  • {key}: {value}")
                        
                        break
                else:
                    print("❌ No flight service results found in response")
            else:
                print("❌ No booking results found in response")
                print(f"Response: {json.dumps(result, indent=2)}")
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - this may indicate agents are still processing")
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - make sure orchestrator is running on port 9001")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_fully_booked_scenario():
    """Test fully booked flight scenario (Tokyo route)."""
    
    orchestrator_url = "http://localhost:9001/book-holiday"
    
    # Test booking request - using Tokyo route (should be fully booked)
    booking_request = {
        "destination": "Tokyo",
        "departure_city": "Delhi",
        "departure_date": "2025-08-15", 
        "return_date": "2025-08-20",
        "passengers": 2,
        "budget": 80000,
        "preferences": {
            "flight_class": "Economy",
            "hotel_rating": 4,
            "transport": "Cab"
        }
    }
    
    print("\n\n🧪 Testing Fully Booked Flight Scenario")
    print("=" * 60)
    print(f"📅 Request: {json.dumps(booking_request, indent=2)}")
    print("=" * 60)
    
    try:
        print("📤 Sending fully booked scenario request...")
        response = requests.post(orchestrator_url, json=booking_request, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Request processed!")
            print("\n🎫 REBOOKING SCENARIO RESPONSE:")
            print("=" * 60)
            
            if 'results' in result:
                for service_result in result['results']:
                    if service_result['service'] == 'flight':
                        print(f"📋 Service: {service_result['service'].upper()}")
                        print(f"📊 Status: {service_result['status']}")
                        print("\n📝 REBOOKING INFORMATION:")
                        print("-" * 40)
                        print(service_result['message'])
                        print("-" * 40)
                        break
                        
        else:
            print(f"❌ Request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing fully booked scenario: {e}")

if __name__ == "__main__":
    print("🚀 Starting Enhanced Orchestrator Test Suite")
    print("🔧 Make sure all agents are running before testing...")
    time.sleep(3)
    
    # Test 1: Comprehensive flight booking
    test_comprehensive_flight_booking()
    
    # Wait between tests
    time.sleep(2)
    
    # Test 2: Fully booked scenario
    test_fully_booked_scenario()
    
    print("\n✅ Test suite completed!")
    print("🎯 Check the output above for detailed flight ticket status display")
