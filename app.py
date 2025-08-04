from flask import Flask, jsonify, request
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.cab_agent import CabAgent

app = Flask(__name__)

# Initialize agents
flight_agent = FlightAgent()
hotel_agent = HotelAgent()
cab_agent = CabAgent()

@app.route('/book/flight', methods=['POST'])
def book_flight():
    data = request.get_json()
    result = flight_agent.book_flight(data)
    return jsonify(result)

@app.route('/book/hotel', methods=['POST'])
def book_hotel():
    data = request.get_json()
    result = hotel_agent.book_hotel(data)
    return jsonify(result)

@app.route('/book/cab', methods=['POST'])
def book_cab():
    data = request.get_json()
    result = cab_agent.book_cab(data)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
