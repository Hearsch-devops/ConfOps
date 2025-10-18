from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# PostgreSQL database credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://conf_user:conf_pass@192.168.48.153:5432/conference_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Booking model
class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    attendees = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.String(255))
    modification_count = db.Column(db.Integer, default=0)

# Ensure tables are created
with app.app_context():
    db.create_all()

# Create a new booking
@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400

        required_fields = ['room_id', 'name', 'email', 'date', 'time', 'duration', 'attendees']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400

        booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        booking_time = datetime.strptime(data['time'], '%H:%M').time()

        new_booking = Booking(
            room_id=data['room_id'],
            name=data['name'],
            email=data['email'],
            date=booking_date,
            time=booking_time,
            duration=data['duration'],
            attendees=data['attendees'],
            purpose=data.get('purpose', '')
        )

        db.session.add(new_booking)
        db.session.commit()

        return jsonify({'id': new_booking.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Check availability for a room
@app.route('/api/bookings/check-availability', methods=['POST'])
def check_availability():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        date = data.get('date')
        time = data.get('time')
        duration = data.get('duration')
        exclude_booking_id = data.get('exclude_booking_id', None)

        if not (room_id and date and time and duration):
            return jsonify({'error': 'Missing required fields'}), 400

        booking_date = datetime.strptime(date, '%Y-%m-%d').date()
        booking_time = datetime.strptime(time, '%H:%M').time()

        # Check for overlapping bookings
        query = Booking.query.filter_by(room_id=room_id, date=booking_date)
        if exclude_booking_id:
            query = query.filter(Booking.id != int(exclude_booking_id))

        overlapping = []
        for b in query.all():
            b_start = datetime.combine(b.date, b.time)
            b_end = b_start + timedelta(minutes=b.duration)
            new_start = datetime.combine(booking_date, booking_time)
            new_end = new_start + timedelta(minutes=duration)

            if new_start < b_end and b_start < new_end:
                overlapping.append(b)

        available = len(overlapping) == 0
        return jsonify({'available': available})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get booking by ID
@app.route('/api/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        return jsonify({
            'id': booking.id,
            'room_id': booking.room_id,
            'name': booking.name,
            'email': booking.email,
            'date': booking.date.isoformat(),
            'time': booking.time.strftime('%H:%M'),
            'duration': booking.duration,
            'attendees': booking.attendees,
            'purpose': booking.purpose,
            'modification_count': booking.modification_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update booking (change reservation)
@app.route('/api/bookings/<int:booking_id>', methods=['PUT'])
def update_booking(booking_id):
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        if booking.modification_count >= 1:
            return jsonify({'error': 'Booking can only be modified once'}), 400

        data = request.get_json()
        if 'date' in data:
            booking.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        if 'time' in data:
            booking.time = datetime.strptime(data['time'], '%H:%M').time()
        if 'duration' in data:
            booking.duration = data['duration']
        if 'attendees' in data:
            booking.attendees = data['attendees']
        if 'purpose' in data:
            booking.purpose = data['purpose']

        booking.modification_count += 1

        db.session.commit()
        return jsonify({'message': 'Booking updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get all rooms (dummy data for frontend)
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = [
        {'id': 1, 'name': 'Executive Board Room', 'capacity': 12},
        {'id': 2, 'name': 'Innovation Hub', 'capacity': 8},
        {'id': 3, 'name': 'Focus Room', 'capacity': 4}
    ]
    return jsonify(rooms)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
