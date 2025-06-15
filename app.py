from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import os
import sqlite3
import random

# Flask app configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yoqilgi_stansiya.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'yoqilgi_stansiya_secret_key'

# Initialize database
db = SQLAlchemy(app)

@app.context_processor
def inject_unread_messages_count():
    if session.get('is_admin'):
        unread_messages_count = Message.query.filter_by(is_read=False).count()
        return dict(unread_messages_count=unread_messages_count)
    return dict(unread_messages_count=0)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Station(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(20))
    opening_hours = db.Column(db.String(100))
    has_shop = db.Column(db.Boolean, default=False)
    has_cafe = db.Column(db.Boolean, default=False)
    has_carwash = db.Column(db.Boolean, default=False)
    has_toilet = db.Column(db.Boolean, default=False)
    accepts_card = db.Column(db.Boolean, default=True)
    is_open = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Fuel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # AI-92, AI-95, Diesel, Gas
    price = db.Column(db.Float, nullable=False)
    available = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User modeli bilan aloqa qo'shildi
    user = db.relationship('User', backref='reviews')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    user = db.relationship('User', backref='messages')

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def index():
    stations = Station.query.all()
    return render_template('index.html', stations=stations)

@app.route('/stations')
def stations():
    stations = Station.query.all()
    return render_template('stations.html', stations=stations)

@app.route('/station/<int:station_id>')
def station_detail(station_id):
    station = Station.query.get_or_404(station_id)
    fuels = Fuel.query.filter_by(station_id=station_id).all()
    reviews = Review.query.filter_by(station_id=station_id).order_by(Review.created_at.desc()).all()
    
    # Get price history for charts
    price_history = {}
    for fuel in fuels:
        history = PriceHistory.query.filter_by(
            station_id=station_id, 
            fuel_type=fuel.type
        ).order_by(PriceHistory.recorded_at.desc()).limit(10).all()
        
        price_history[fuel.type] = {
            'dates': [h.recorded_at.strftime('%Y-%m-%d') for h in history],
            'prices': [h.price for h in history]
        }
    
    # Check if station is in user's favorites
    is_favorite = False
    if 'user_id' in session:
        favorite = Favorite.query.filter_by(
            user_id=session['user_id'],
            station_id=station_id
        ).first()
        is_favorite = favorite is not None
    
    return render_template(
        'station_detail.html', 
        station=station, 
        fuels=fuels, 
        reviews=reviews, 
        price_history=json.dumps(price_history),
        is_favorite=is_favorite
    )

@app.route('/search')
def search():
    query = request.args.get('q', '')
    fuel_type = request.args.get('fuel_type', '')
    city = request.args.get('city', '')
    
    stations_query = Station.query
    
    if query:
        stations_query = stations_query.filter(
            (Station.name.ilike(f'%{query}%')) | 
            (Station.address.ilike(f'%{query}%'))
        )
    
    if city:
        stations_query = stations_query.filter(Station.city == city)
    
    stations = stations_query.all()
    
    # Filter by fuel type if specified
    if fuel_type:
        filtered_stations = []
        for station in stations:
            fuels = Fuel.query.filter_by(station_id=station.id, type=fuel_type).all()
            if fuels:
                filtered_stations.append(station)
        stations = filtered_stations
    
    return render_template('search_results.html', stations=stations, query=query)

@app.route('/get_stations')
def get_stations():
    stations = Station.query.all()
    stations_data = []
    
    for station in stations:
        fuels = Fuel.query.filter_by(station_id=station.id).all()
        fuel_data = {}
        
        for fuel in fuels:
            fuel_data[fuel.type] = {
                'price': fuel.price,
                'available': fuel.available
            }
        
        stations_data.append({
            'id': station.id,
            'name': station.name,
            'lat': station.latitude,
            'lng': station.longitude,
            'address': station.address,
            'city': station.city,
            'is_open': station.is_open,
            'fuels': fuel_data
        })
    
    return jsonify(stations_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('register.html')
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.route('/submit_review/<int:station_id>', methods=['POST'])
def submit_review(station_id):
    if 'user_id' not in session:
        flash('You need to log in to submit a review', 'error')
        return redirect(url_for('login'))
    
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')
    
    # Check if user already reviewed this station
    existing_review = Review.query.filter_by(
        user_id=session['user_id'],
        station_id=station_id
    ).first()
    
    if existing_review:
        # Update existing review
        existing_review.rating = rating
        existing_review.comment = comment
        existing_review.created_at = datetime.utcnow()
    else:
        # Create new review
        new_review = Review(
            user_id=session['user_id'],
            station_id=station_id,
            rating=rating,
            comment=comment
        )
        db.session.add(new_review)
    
    db.session.commit()
    flash('Thank you for your review!', 'success')
    return redirect(url_for('station_detail', station_id=station_id))

@app.route('/toggle_favorite/<int:station_id>')
def toggle_favorite(station_id):
    if 'user_id' not in session:
        flash('You need to log in to add favorites', 'error')
        return redirect(url_for('login'))
    
    existing_favorite = Favorite.query.filter_by(
        user_id=session['user_id'],
        station_id=station_id
    ).first()
    
    if existing_favorite:
        # Remove from favorites
        db.session.delete(existing_favorite)
        db.session.commit()
        return jsonify({'status': 'removed'})
    else:
        # Add to favorites
        new_favorite = Favorite(
            user_id=session['user_id'],
            station_id=station_id
        )
        db.session.add(new_favorite)
        db.session.commit()
        return jsonify({'status': 'added'})

@app.route('/my_favorites')
def my_favorites():
    if 'user_id' not in session:
        flash('You need to log in to view favorites', 'error')
        return redirect(url_for('login'))
    
    favorites = Favorite.query.filter_by(user_id=session['user_id']).all()
    favorite_stations = []
    
    for favorite in favorites:
        station = Station.query.get(favorite.station_id)
        if station:
            favorite_stations.append(station)
    
    return render_template('favorites.html', stations=favorite_stations)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('You need to log in to send messages', 'error')
            return redirect(url_for('login'))
        
        subject = request.form.get('subject')
        message_text = request.form.get('message')
        
        new_message = Message(
            user_id=session['user_id'],
            subject=subject,
            message=message_text
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        flash('Your message has been sent. We will respond shortly.', 'success')
        return redirect(url_for('my_messages'))
    
    return render_template('contact.html')

@app.route('/my_messages')
def my_messages():
    if 'user_id' not in session:
        flash('You need to log in to view messages', 'error')
        return redirect(url_for('login'))
    
    messages = Message.query.filter_by(user_id=session['user_id']).order_by(Message.created_at.desc()).all()
    return render_template('my_messages.html', messages=messages)

# Admin routes
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    stations_count = Station.query.count()
    users_count = User.query.count()
    reviews_count = Review.query.count()
    unread_messages_count = Message.query.filter_by(is_read=False).count()
    
    return render_template(
        'admin/dashboard.html', 
        stations_count=stations_count,
        users_count=users_count,
        reviews_count=reviews_count,
        unread_messages_count=unread_messages_count
    )

@app.route('/admin/stations')
def admin_stations():
    if not session.get('is_admin'):
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    stations = Station.query.all()
    return render_template('admin/stations.html', stations=stations)

@app.route('/admin/station/<int:station_id>', methods=['GET', 'POST'])
def admin_station_edit(station_id):
    if not session.get('is_admin'):
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    station = Station.query.get_or_404(station_id)
    fuels = Fuel.query.filter_by(station_id=station_id).all()
    
    if request.method == 'POST':
        # Update station details
        station.name = request.form.get('name')
        station.address = request.form.get('address')
        station.city = request.form.get('city')
        station.latitude = float(request.form.get('latitude'))
        station.longitude = float(request.form.get('longitude'))
        station.phone = request.form.get('phone')
        station.opening_hours = request.form.get('opening_hours')
        station.has_shop = 'has_shop' in request.form
        station.has_cafe = 'has_cafe' in request.form
        station.has_carwash = 'has_carwash' in request.form
        station.has_toilet = 'has_toilet' in request.form
        station.accepts_card = 'accepts_card' in request.form
        station.is_open = 'is_open' in request.form
        
        # Update fuels
        for fuel in fuels:
            new_price = float(request.form.get(f'price_{fuel.id}'))
            is_available = f'available_{fuel.id}' in request.form
            
            # If price changed, add to history
            if fuel.price != new_price:
                price_history = PriceHistory(
                    station_id=station_id,
                    fuel_type=fuel.type,
                    price=new_price
                )
                db.session.add(price_history)
            
            # Update fuel
            fuel.price = new_price
            fuel.available = is_available
        
        db.session.commit()
        flash('Station updated successfully', 'success')
        return redirect(url_for('admin_stations'))
    
    return render_template('admin/station_edit.html', station=station, fuels=fuels)

@app.route('/admin/station/add', methods=['GET', 'POST'])
def admin_station_add():
    if not session.get('is_admin'):
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Create new station
        new_station = Station(
            name=request.form.get('name'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            latitude=float(request.form.get('latitude')),
            longitude=float(request.form.get('longitude')),
            phone=request.form.get('phone'),
            opening_hours=request.form.get('opening_hours'),
            has_shop='has_shop' in request.form,
            has_cafe='has_cafe' in request.form,
            has_carwash='has_carwash' in request.form,
            has_toilet='has_toilet' in request.form,
            accepts_card='accepts_card' in request.form,
            is_open='is_open' in request.form
        )
        
        db.session.add(new_station)
        db.session.commit()
        
        # Add fuels
        fuel_types = ['AI-92', 'AI-95', 'Diesel', 'Gas']
        for fuel_type in fuel_types:
            if request.form.get(f'add_{fuel_type.lower().replace("-", "")}') == 'on':
                price = float(request.form.get(f'price_{fuel_type.lower().replace("-", "")}'))
                
                new_fuel = Fuel(
                    station_id=new_station.id,
                    type=fuel_type,
                    price=price,
                    available=True
                )
                
                db.session.add(new_fuel)
                
                # Add initial price history
                price_history = PriceHistory(
                    station_id=new_station.id,
                    fuel_type=fuel_type,
                    price=price
                )
                db.session.add(price_history)
        
        db.session.commit()
        flash('Station added successfully', 'success')
        return redirect(url_for('admin_stations'))
    
    return render_template('admin/station_add.html')

@app.route('/admin/station/delete/<int:station_id>')
def admin_station_delete(station_id):
    if not session.get('is_admin'):
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    station = Station.query.get_or_404(station_id)
    
    # Delete associated data
    Fuel.query.filter_by(station_id=station_id).delete()
    PriceHistory.query.filter_by(station_id=station_id).delete()
    Review.query.filter_by(station_id=station_id).delete()
    Favorite.query.filter_by(station_id=station_id).delete()
    
    # Delete station
    db.session.delete(station)
    db.session.commit()
    
    flash('Station deleted successfully', 'success')
    return redirect(url_for('admin_stations'))

@app.route('/admin/messages')
def admin_messages():
    if not session.get('is_admin'):
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages)

@app.route('/admin/message/<int:message_id>', methods=['GET', 'POST'])
def admin_message_reply(message_id):
    if not session.get('is_admin'):
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    message = Message.query.get_or_404(message_id)
    user = User.query.get(message.user_id)
    
    if not message.is_read:
        message.is_read = True
        db.session.commit()
    
    if request.method == 'POST':
        message.response = request.form.get('response')
        message.responded_at = datetime.utcnow()
        db.session.commit()
        flash('Response sent successfully', 'success')
        return redirect(url_for('admin_messages'))
    
    unread_messages_count = Message.query.filter_by(is_read=False).count()
    return render_template('admin/message_reply.html', message=message, user=user, unread_messages_count=unread_messages_count)
    # Mark as read when viewing
    if not message.is_read:
        message.is_read = True
        db.session.commit()
    
    return render_template('admin/message_reply.html', message=message, user=user)

@app.route('/admin/users')
def admin_users():
    if not session.get('is_admin'):
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

# Initialize the database and create demo data
def init_db():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created with username 'admin' and password 'admin'")
        
        # Check if we need to create demo data
        if Station.query.count() == 0:
            create_demo_data()
            print("Demo data created successfully")

def create_demo_data():
    # Sample cities
    cities = ['Tashkent', 'Samarkand', 'Bukhara', 'Namangan', 'Andijan']
    
    # Sample station names
    station_prefixes = ['Uzbekneftegaz', 'Lukoil', 'Shox', 'Ipak', 'Jizzax', 'Osiyo']
    
    # Generate random stations
    for i in range(15):
        city = random.choice(cities)
        
        # Create a station
        station = Station(
            name=f"{random.choice(station_prefixes)} #{i+1}",
            address=f"Street {random.randint(1, 100)}, {city}",
            city=city,
            latitude=41.2 + random.uniform(-0.5, 0.5),
            longitude=69.2 + random.uniform(-0.5, 0.5),
            phone=f"+998 9{random.randint(0, 9)} {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}",
            opening_hours="24/7" if random.random() > 0.3 else f"{random.randint(6, 9)}:00 - {random.randint(20, 23)}:00",
            has_shop=random.random() > 0.3,
            has_cafe=random.random() > 0.5,
            has_carwash=random.random() > 0.6,
            has_toilet=random.random() > 0.2,
            accepts_card=random.random() > 0.1,
            is_open=random.random() > 0.1
        )
        
        db.session.add(station)
        db.session.commit()
        
        # Create fuels for the station
        fuel_types = ['AI-92', 'AI-95', 'Diesel', 'Gas']
        base_prices = {'AI-92': 7000, 'AI-95': 8000, 'Diesel': 7500, 'Gas': 4000}
        
        for fuel_type in fuel_types:
            if random.random() > 0.2:  # 80% chance to have this fuel type
                price = base_prices[fuel_type] + random.randint(-200, 200)
                
                fuel = Fuel(
                    station_id=station.id,
                    type=fuel_type,
                    price=price,
                    available=random.random() > 0.1
                )
                
                db.session.add(fuel)
                
                # Create price history for the last 10 days
                for day in range(10):
                    history_date = datetime.utcnow() - timedelta(days=day)
                    history_price = price - random.randint(-100, 100)
                    
                    price_history = PriceHistory(
                        station_id=station.id,
                        fuel_type=fuel_type,
                        price=history_price,
                        recorded_at=history_date
                    )
                    
                    db.session.add(price_history)
        
        db.session.commit()
    
    # Create regular users
    user_names = ['user1', 'user2', 'user3']
    for username in user_names:
        user = User(
            username=username,
            email=f"{username}@example.com",
            password=generate_password_hash('password')
        )
        
        db.session.add(user)
    
    db.session.commit()
    
    # Add some reviews
    users = User.query.filter(User.username != 'admin').all()
    stations = Station.query.all()
    
    for i in range(30):
        user = random.choice(users)
        station = random.choice(stations)
        
        review = Review(
            user_id=user.id,
            station_id=station.id,
            rating=random.randint(1, 5),
            comment=f"This is a sample review #{i+1} for station {station.name}. " +
                    random.choice([
                        "Good service and clean facilities.",
                        "The prices are reasonable.",
                        "I had to wait in line for too long.",
                        "Very helpful staff.",
                        "The location is convenient.",
                        "They need to improve their service."
                    ]),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        
        db.session.add(review)
    
    db.session.commit()
    
    # Add some messages
    message_subjects = [
        "Incorrect fuel price",
        "Station not on map",
        "Great customer service",
        "App suggestion",
        "Website feedback"
    ]
    
    message_bodies = [
        "I noticed that the fuel price for AI-92 at Station #5 is incorrect. It should be 7200 not 7000.",
        "Please add the new gas station on Bobur Street to your map.",
        "I wanted to thank the staff at Lukoil #3 for their excellent service yesterday.",
        "It would be great if you could add a feature to filter stations by services offered.",
        "The website is great but the search function could be improved."
    ]
    
    for i in range(10):
        user = random.choice(users)
        
        message = Message(
            user_id=user.id,
            subject=random.choice(message_subjects),
            message=random.choice(message_bodies) + f" - Message #{i+1}",
            is_read=random.random() > 0.5,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 15))
        )
        
        if message.is_read and random.random() > 0.5:
            message.response = "Thank you for your message. We appreciate your feedback and will take appropriate action."
            message.responded_at = message.created_at + timedelta(days=random.randint(1, 3))
        
        db.session.add(message)
    
    db.session.commit()

if __name__ == '__main__':
   with app.app_context():
        # db.drop_all()  # Eski jadvallarni o'chirish
        # init_db()      # Yangi jadvallar va demo ma'lumotlarni yaratish
        app.run(debug=True)