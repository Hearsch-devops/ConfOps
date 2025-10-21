from flask import Flask, request, jsonify, send_from_directory
import traceback
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import sys

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# PostgreSQL Database Configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 
    'postgresql://conf_user:conf_pass@postgres:5432/conference_db')

print(f"=== DATABASE CONFIGURATION ===", file=sys.stderr)
print(f"DATABASE_URL: {DATABASE_URL}", file=sys.stderr)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # Enable SQL logging for debugging

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
    duration = db.Column(db.Integer, nullable=False)
    attendees = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='confirmed')
    modification_count = db.Column(db.Integer, default=0)
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
    if isinstance(booking_time, str):
        booking_time = datetime.strptime(booking_time, '%H:%M').time()
    
    booking_datetime = datetime.combine(booking_date, booking_time)
    booking_end = booking_datetime + timedelta(minutes=duration)
    
    query = Booking.query.filter_by(
        room_id=room_id,
        date=booking_date,
        status='confirmed'
    )
    
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    
    existing_bookings = query.all()
    
    for existing in existing_bookings:
        existing_datetime = datetime.combine(existing.date, existing.time)
        existing_end = existing_datetime + timedelta(minutes=existing.duration)
        
        if (booking_datetime < existing_end and booking_end > existing_datetime):
            return True, f"Conflicts with existing booking from {existing.time.strftime('%H:%M')} to {existing_end.strftime('%H:%M')}"
    
    return False, None


# Routes - Serve Frontend
@app.route('/')
def home():
    """Serve the main HTML file"""
    try:
        # Try to serve from current directory
        return render_template('.', 'index.html')
    except Exception as e:
        print(f"Error serving index.html: {str(e)}", file=sys.stderr)
        return jsonify({'error': 'index.html not found', 'details': str(e)}), 404


# Debug/Health Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/init-db', methods=['POST'])
def init_database():
    """Initialize database with sample data"""
    try:
        print("=== INITIALIZING DATABASE ===", file=sys.stderr)
        db.create_all()
        print("Tables created successfully", file=sys.stderr)
        
        if Room.query.count() > 0:
            return jsonify({'message': 'Database already initialized'}), 200
        
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
            print(f"Added room: {room.name}", file=sys.stderr)
        
        db.session.commit()
        print("Database initialized successfully", file=sys.stderr)
        return jsonify({'message': 'Database initialized successfully', 'rooms_added': len(rooms)}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing database: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


# Room Routes
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    """Get all conference rooms"""
    try:
        rooms = Room.query.all()
        return jsonify([room.to_dict() for room in rooms]), 200
    except Exception as e:
        print(f"Error fetching rooms: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """Get a specific room by ID"""
    try:
        room = Room.query.get_or_404(room_id)
        return jsonify(room.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Booking Routes
@app.route('/api/bookings', methods=['GET'])
def list_bookings():
    """Get all bookings with optional filters"""
    try:
        room_id = request.args.get('room_id', type=int)
        date = request.args.get('date')
        status = request.args.get('status')
        
        query = Booking.query
        
        if room_id:
            query = query.filter_by(room_id=room_id)
        if date:
            try:
                query = query.filter_by(date=datetime.strptime(date, '%Y-%m-%d').date())
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400
        if status:
            query = query.filter_by(status=status)
        
        bookings = query.order_by(Booking.date.desc(), Booking.time.desc()).all()
        return jsonify([booking.to_dict() for booking in bookings]), 200
    except Exception as e:
        print(f"Error listing bookings: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/bookings/<int:booking_id>', methods=['GET'])
def get_single_booking(booking_id):
    """Get a specific booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        return jsonify(booking.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bookings/check-availability', methods=['POST'])
def check_availability():
    """Check if a time slot is available"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['room_id', 'date', 'time', 'duration']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        booking_time = datetime.strptime(data['time'], '%H:%M').time()
        duration = int(data['duration'])
        room_id = int(data['room_id'])
        exclude_booking_id = data.get('exclude_booking_id')
        
        has_conflict, conflict_message = check_time_conflict(
            room_id, booking_date, booking_time, duration, exclude_booking_id
        )
        
        if has_conflict:
            return jsonify({'available': False, 'message': conflict_message}), 200
        
        return jsonify({'available': True, 'message': 'Time slot is available'}), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid date or time format: {str(e)}'}), 400
    except Exception as e:
        print(f"Error checking availability: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/bookings', methods=['POST'])
def create_new_booking():
    """Create a new booking"""
    try:
        print("=== CREATE BOOKING REQUEST ===", file=sys.stderr)
        print(f"Content-Type: {request.content_type}", file=sys.stderr)
        
        data = request.get_json()
        print(f"Request data: {data}", file=sys.stderr)
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        required_fields = ['room_id', 'name', 'email', 'date', 'time', 'duration', 'attendees']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        room = Room.query.get(data['room_id'])
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        if not room.is_available:
            return jsonify({'error': 'Room is not available'}), 400
        
        if data['attendees'] > room.capacity:
            return jsonify({'error': f'Room capacity is {room.capacity}, cannot accommodate {data["attendees"]} attendees'}), 400
        
        booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        booking_time = datetime.strptime(data['time'], '%H:%M').time()
        duration = int(data['duration'])
        
        if duration <= 0 or duration > 480:
            return jsonify({'error': 'Duration must be between 1 and 480 minutes'}), 400
        
        has_conflict, conflict_message = check_time_conflict(
            data['room_id'], booking_date, booking_time, duration
        )
        
        if has_conflict:
            return jsonify({'error': conflict_message}), 409
        
        price = calculate_price(room.name, duration)
        
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
        
        db.session.add(booking)
        db.session.commit()
        print(f"Booking created successfully: {booking.id}", file=sys.stderr)
        return jsonify(booking.to_dict()), 201
        
    except ValueError as e:
        return jsonify({'error': f'Invalid date or time format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error creating booking: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@app.route('/api/bookings/<int:booking_id>', methods=['PUT'])
def modify_booking(booking_id):
    """Update a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if booking.modification_count >= 1:
            return jsonify({'error': 'This booking has already been modified once. No further changes allowed.'}), 403
        
        if booking.status != 'confirmed':
            return jsonify({'error': 'Only confirmed bookings can be modified'}), 400
        
        if 'room_id' in data and int(data['room_id']) != booking.room_id:
            return jsonify({'error': 'Room cannot be changed'}), 400
        
        booking_date = booking.date
        booking_time = booking.time
        duration = booking.duration
        
        if 'date' in data:
            booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        if 'time' in data:
            booking_time = datetime.strptime(data['time'], '%H:%M').time()
        if 'duration' in data:
            duration = int(data['duration'])
            if duration <= 0 or duration > 480:
                return jsonify({'error': 'Duration must be between 1 and 480 minutes'}), 400
        
        has_conflict, conflict_message = check_time_conflict(
            booking.room_id, booking_date, booking_time, duration, booking_id
        )
        
        if has_conflict:
            return jsonify({'error': conflict_message}), 409
        
        if 'attendees' in data:
            room = Room.query.get(booking.room_id)
            attendees = int(data['attendees'])
            if attendees > room.capacity:
                return jsonify({'error': f'Room capacity is {room.capacity}'}), 400
            booking.attendees = attendees
        
        if 'date' in data:
            booking.date = booking_date
        if 'time' in data:
            booking.time = booking_time
        if 'duration' in data:
            booking.duration = duration
            booking.price = calculate_price(booking.room.name, duration)
        if 'purpose' in data:
            booking.purpose = data['purpose']
        
        booking.modification_count += 1
        booking.updated_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify(booking.to_dict()), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error modifying booking: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def remove_booking(booking_id):
    """Delete a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        db.session.delete(booking)
        db.session.commit()
        return jsonify({'message': 'Booking deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting booking: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.errorhandler(Exception)
def handle_uncaught_exception(e):
    """Handle any uncaught exception"""
    print("=== UNCAUGHT EXCEPTION ===", file=sys.stderr)
    traceback.print_exc()
    return jsonify({
        'error': 'Internal Server Error',
        'details': str(e),
        'type': type(e).__name__
    }), 500


if __name__ == '__main__':
    with app.app_context():
        try:
            print("=== STARTING APPLICATION ===", file=sys.stderr)
            db.create_all()
            print("Database tables created/verified", file=sys.stderr)
        except Exception as e:
            print('=== ERROR DURING DB INITIALIZATION ===', file=sys.stderr)
            traceback.print_exc()
    
    print("=== FLASK SERVER STARTING ===", file=sys.stderr)
    app.run(debug=True, host='0.0.0.0', port=5000)