#!/usr/bin/env python3
"""
Direct test of enhanced flight agent to see actual response format.
"""

import asyncio
import requests
import json

async def test_direct_flight_agent():
    """Test the enhanced flight agent directly."""
    
    url = "http://localhost:5002/"
    
    # Direct A2A message format
    message_data = {
        "jsonrpc": "2.0",
        "id": "test-123",
        "method": "send_message", 
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Book a comprehensive round-trip flight with full details:\n\nFLIGHT REQUIREMENTS:\n• Origin: Delhi\n• Destination: Mumbai\n• Departure Date: 2025-08-15\n• Passengers: 2 adults\n• Class: Economy\n• Trip Type: Round-trip\n\nREQUESTED DETAILS:\n• Provide complete booking confirmation with booking ID\n• Include flight numbers, aircraft type, and seat availability\n• Show departure/arrival times and gate information\n• Display total price breakdown and payment confirmation\n• If flights are fully booked, provide rebooking options with alternative flights\n• Include baggage allowance and check-in information\n• Show behind-the-scenes booking process and database operations\n\nPREFERENCES:\n• Flexible booking with free cancellation\n• Online check-in capability\n• Aisle seats preferred\n• Meal preferences: Standard\n\nPlease provide comprehensive flight booking details including all backend operations and booking confirmations."
                    }
                ]
            }
        }
    }
    
    print("🧪 Testing Enhanced Flight Agent Directly")
    print("=" * 60)
    
    try:
        response = requests.post(url, json=message_data, headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Direct flight agent test successful!")
            print("\n📝 Raw Response:")
            print(json.dumps(result, indent=2))
            
            # Extract the actual response text
            if 'result' in result and 'message' in result['result']:
                message = result['result']['message']
                if 'parts' in message and message['parts']:
                    response_text = message['parts'][0].get('text', '')
                    print("\n🎫 COMPREHENSIVE FLIGHT RESPONSE:")
                    print("=" * 60)
                    print(response_text)
                    print("=" * 60)
                    
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing direct flight agent: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_flight_agent())
