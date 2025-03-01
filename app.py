from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from math import radians, cos, sin, asin, sqrt


app = Flask(__name__)

# SQLite config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///towers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

def haversine(lat1, lon1, lat2, lon2):
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email
        }

# Tower model with foreign key to User
class Tower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Links to User table
    user = db.relationship('User', backref='towers')  # Relationship for easy access

    def to_dict(self):
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "user_id": self.user_id,
            "user": self.user.to_dict()  # Include user details in response
        }

# Create tables
with app.app_context():
    db.create_all()

# GET all towers
@app.route('/towers', methods=['GET'])
def get_towers():
    towers = Tower.query.all()
    return jsonify([tower.to_dict() for tower in towers]), 200

# GET one tower by ID
@app.route('/towers/<int:tower_id>', methods=['GET'])
def get_tower(tower_id):
    tower = Tower.query.get(tower_id)
    if tower:
        return jsonify(tower.to_dict()), 200
    return jsonify({"error": "Tower not found"}), 404

# POST a new tower
@app.route('/towers', methods=['POST'])
def create_tower():
    data = request.get_json()
    if not data or 'latitude' not in data or 'longitude' not in data or 'user_id' not in data:
        return jsonify({"error": "Missing latitude, longitude, or user_id"}), 400
    
    try:
        lat = float(data['latitude'])
        lon = float(data['longitude'])
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({"error": "Invalid GPS coordinates"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Latitude and longitude must be numbers"}), 400

    # Check if user_id exists
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Make sure we aren't within 1km of an existing tower
    for tower in Tower.query.all():
        if haversine(tower.latitude, tower.longitude, lat, lon) < 1.0:
            return jsonify({"error": "Tower already exists within 1km"}), 400

    new_tower = Tower(latitude=lat, longitude=lon, user_id=data['user_id'])
    db.session.add(new_tower)
    db.session.commit()
    return jsonify(new_tower.to_dict()), 201

# POST a new user
@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or 'first_name' not in data or 'last_name' not in data or 'email' not in data:
        return jsonify({"error": "Missing first_name, last_name, or email"}), 400
    
    # Check for duplicate email
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already exists"}), 400

    new_user = User(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email']
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify(new_user.to_dict()), 201

# GET all users
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

# GET one user by ID
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get(user_id)
    if user:
        return jsonify(user.to_dict()), 200
    return jsonify({"error": "User not found"}), 404

# GET all towers for a user by User ID
@app.route('/users/<int:user_id>/towers', methods=['GET'])
def get_towers_by_user_id(user_id):
    towers = Tower.query.filter_by(user_id=user_id).all()
    result = jsonify([tower.to_dict() for tower in towers])
    print([tower.to_dict() for tower in towers])
    return result, 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)