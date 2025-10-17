from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from flask import Flask, render_template
import os

app = Flask(__name__)
CORS(app)

# PostgreSQL Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 
    'postgresql://admin:password@192.168.48.153:5432/conference_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Room pricing in rupees per 30 minutes
ROOM_PRICING = {
    'Executive Board Room': 1000,
    'Innovation Hub': 1500,
    'Focus Room': 500
}

# Models
class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    capacity = db.Column(db.Integer, nullable=False)
    floor = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    amenities = db.Column(db.String(500))
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='room', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'floor': self.floor,
            'description': self.description,
            'amenities': self.amenities,
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat()
        }


class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    attendees = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)  # Total price in rupees
    status = db.Column(db.String(20), default='confirmed')  # confirmed, cancelled, completed
    modification_count = db.Column(db.Integer, default=0)  # Track number of modifications
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'room_name': self.room.name,
            'name': self.name,
            'email': self.email,
            'date': self.date.isoformat(),
            'time': self.time.strftime('%H:%M'),
            'duration': self.duration,
            'attendees': self.attendees,
            'purpose': self.purpose,
            'price': self.price,
            'status': self.status,
            'modification_count': self.modification_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


def calculate_price(room_name, duration):
    """Calculate price based on room and duration"""
    base_price = ROOM_PRICING.get(room_name, 1000)
    return (base_price / 30) * duration


def check_time_conflict(room_id, booking_date, booking_time, duration, exclude_booking_id=None):
    """Check if there's a time conflict for the given booking"""
    # Convert string time to datetime.time if needed
    if isinstance(booking_time, str):
        booking_time = datetime.strptime(booking_time, '%H:%M').time()
    
    # Calculate end time for the new booking
    booking_datetime = datetime.combine(booking_date, booking_time)
    booking_end = booking_datetime + timedelta(minutes=duration)
    
    # Query all confirmed bookings for the same room and date
    query = Booking.query.filter_by(
        room_id=room_id,
        date=booking_date,
        status='confirmed'
    )
    
    # Exclude current booking if updating
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    
    existing_bookings = query.all()
    
    # Check for time conflicts
    for existing in existing_bookings:
        existing_datetime = datetime.combine(existing.date, existing.time)
        existing_end = existing_datetime + timedelta(minutes=existing.duration)
        
        # Check if times overlap
        if (booking_datetime < existing_end and booking_end > existing_datetime):
            return True, f"Conflicts with existing booking from {existing.time.strftime('%H:%M')} to {existing_end.strftime('%H:%M')}"
    
    return False, None


# Routes - Rooms
@app.route('/')
def home():
    return render_template('index.html')
    
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    """Get all conference rooms"""
    rooms = Room.query.all()
    return jsonify([room.to_dict() for room in rooms]), 200


@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """Get a specific room by ID"""
    room = Room.query.get_or_404(room_id)
    return jsonify(room.to_dict()), 200


@app.route('/api/rooms', methods=['POST'])
def create_room():
    """Create a new conference room"""
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('capacity'):
        return jsonify({'error': 'Name and capacity are required'}), 400
    
    room = Room(
        name=data['name'],
        capacity=data['capacity'],
        floor=data.get('floor', 1),
        description=data.get('description', ''),
        amenities=data.get('amenities', ''),
        is_available=data.get('is_available', True)
    )
    
    try:
        db.session.add(room)
        db.session.commit()
        return jsonify(room.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
def update_room(room_id):
    """Update a room"""
    room = Room.query.get_or_404(room_id)
    data = request.get_json()
    
    if 'name' in data:
        room.name = data['name']
    if 'capacity' in data:
        room.capacity = data['capacity']
    if 'floor' in data:
        room.floor = data['floor']
    if 'description' in data:
        room.description = data['description']
    if 'amenities' in data:
        room.amenities = data['amenities']
    if 'is_available' in data:
        room.is_available = data['is_available']
    
    try:
        db.session.commit()
        return jsonify(room.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    """Delete a room"""
    room = Room.query.get_or_404(room_id)
    
    try:
        db.session.delete(room)
        db.session.commit()
        return jsonify({'message': 'Room deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Routes - Bookings
@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    """Get all bookings with optional filters"""
    room_id = request.args.get('room_id', type=int)
    date = request.args.get('date')
    status = request.args.get('status')
    
    query = Booking.query
    
    if room_id:
        query = query.filter_by(room_id=room_id)
    if date:
        query = query.filter_by(date=datetime.strptime(date, '%Y-%m-%d').date())
    if status:
        query = query.filter_by(status=status)
    
    bookings = query.order_by(Booking.date.desc(), Booking.time.desc()).all()
    return jsonify([booking.to_dict() for booking in bookings]), 200


@app.route('/api/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Get a specific booking"""
    booking = Booking.query.get_or_404(booking_id)
    return jsonify(booking.to_dict()), 200


@app.route('/api/bookings/check-availability', methods=['POST'])
def check_availability():
    """Check if a time slot is available"""
    data = request.get_json()
    
    required_fields = ['room_id', 'date', 'time', 'duration']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        booking_time = datetime.strptime(data['time'], '%H:%M').time()
        duration = int(data['duration'])
        room_id = int(data['room_id'])
        exclude_booking_id = data.get('exclude_booking_id')
        
        has_conflict, conflict_message = check_time_conflict(
            room_id, booking_date, booking_time, duration, exclude_booking_id
        )
        
        if has_conflict:
            return jsonify({
                'available': False,
                'message': conflict_message
            }), 200
        
        return jsonify({
            'available': True,
            'message': 'Time slot is available'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': 'Invalid date or time format'}), 400


@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Create a new booking"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['room_id', 'name', 'email', 'date', 'time', 'duration', 'attendees']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if room exists
    room = Room.query.get(data['room_id'])
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    # Check if room has enough capacity
    if data['attendees'] > room.capacity:
        return jsonify({'error': f'Room capacity is {room.capacity}, cannot accommodate {data["attendees"]} attendees'}), 400
    
    # Parse date and time
    try:
        booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        booking_time = datetime.strptime(data['time'], '%H:%M').time()
        duration = int(data['duration'])
    except ValueError:
        return jsonify({'error': 'Invalid date or time format'}), 400
    
    # Check for time conflicts
    has_conflict, conflict_message = check_time_conflict(
        data['room_id'], booking_date, booking_time, duration
    )
    
    if has_conflict:
        return jsonify({'error': conflict_message}), 409
    
    # Calculate price
    price = calculate_price(room.name, duration)
    
    # Create booking
    booking = Booking(
        room_id=data['room_id'],
        name=data['name'],
        email=data['email'],
        date=booking_date,
        time=booking_time,
        duration=duration,
        attendees=data['attendees'],
        purpose=data.get('purpose', ''),
        price=price,
        status='confirmed',
        modification_count=0
    )
    
    try:
        db.session.add(booking)
        db.session.commit()
        return jsonify(booking.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/bookings/<int:booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """Update a booking (only allowed once, room cannot be changed)"""
    booking = Booking.query.get_or_404(booking_id)
    data = request.get_json()
    
    # Check if booking has already been modified
    if booking.modification_count >= 1:
        return jsonify({'error': 'This booking has already been modified once. No further changes allowed.'}), 403
    
    # Check if booking is still active
    if booking.status != 'confirmed':
        return jsonify({'error': 'Only confirmed bookings can be modified'}), 400
    
    # Prevent room change
    if 'room_id' in data and int(data['room_id']) != booking.room_id:
        return jsonify({'error': 'Room cannot be changed. You can only modify date, time, duration, and attendees.'}), 400
    
    # Parse new date and time if provided
    booking_date = booking.date
    booking_time = booking.time
    duration = booking.duration
    
    if 'date' in data:
        booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    if 'time' in data:
        booking_time = datetime.strptime(data['time'], '%H:%M').time()
    if 'duration' in data:
        duration = int(data['duration'])
    
    # Check for time conflicts (excluding current booking)
    has_conflict, conflict_message = check_time_conflict(
        booking.room_id, booking_date, booking_time, duration, booking_id
    )
    
    if has_conflict:
        return jsonify({'error': conflict_message}), 409
    
    # Check room capacity if attendees changed
    if 'attendees' in data:
        room = Room.query.get(booking.room_id)
        attendees = data['attendees']
        if attendees > room.capacity:
            return jsonify({'error': f'Room capacity is {room.capacity}, cannot accommodate {attendees} attendees'}), 400
    
    # Update booking fields
    if 'date' in data:
        booking.date = booking_date
    if 'time' in data:
        booking.time = booking_time
    if 'duration' in data:
        booking.duration = duration
        # Recalculate price if duration changed
        booking.price = calculate_price(booking.room.name, duration)
    if 'attendees' in data:
        booking.attendees = data['attendees']
    if 'purpose' in data:
        booking.purpose = data['purpose']
    
    # Increment modification count
    booking.modification_count += 1
    booking.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify(booking.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    """Delete/Cancel a booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        db.session.delete(booking)
        db.session.commit()
        return jsonify({'message': 'Booking deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel a booking (soft delete)"""
    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'cancelled'
    booking.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify(booking.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Utility Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'database': 'connected'}), 200


@app.route('/api/init-db', methods=['POST'])
def init_database():
    """Initialize database with sample data"""
    try:
        # Create tables
        db.create_all()
        
        # Check if rooms already exist
        if Room.query.count() > 0:
            return jsonify({'message': 'Database already initialized'}), 200
        
        # Add sample rooms
        rooms = [
            Room(name='Executive Board Room', capacity=12, floor=5, 
                 description='Premium board room with video conferencing and whiteboard',
                 amenities='Video Conferencing, Whiteboard, Projector'),
            Room(name='Innovation Hub', capacity=8, floor=3,
                 description='Creative space with brainstorming tools and collaboration tech',
                 amenities='Whiteboard, Smart TV, Collaboration Tools'),
            Room(name='Focus Room', capacity=4, floor=2,
                 description='Small meeting room perfect for team discussions',
                 amenities='TV Screen, Whiteboard')
        ]
        
        for room in rooms:
            db.session.add(room)
        
        db.session.commit()
        return jsonify({'message': 'Database initialized successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)