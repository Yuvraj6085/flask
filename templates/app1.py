from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from flask_mail import Mail, Message
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='templates')

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '98c19e1843b31e77d5a7fafaf88370c2')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'mysql+pymysql://root:Bindu@134366@localhost/everlight'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    event_date = db.Column(db.Date, nullable=True)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')

    def __repr__(self):
        return f'<Booking {self.name} - {self.service_type}>'

class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)
    image_path = db.Column(db.String(200), nullable=False)
    animation_type = db.Column(db.String(50), nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<GalleryItem {self.title} - {self.category}>'

class Testimonial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    client_title = db.Column(db.String(100), nullable=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Testimonial {self.client_name} - {self.rating} stars>'

# Routes
@app.route('/')
def home():
    featured_items = GalleryItem.query.filter_by(is_featured=True).limit(6).all()
    testimonials = Testimonial.query.filter_by(is_approved=True).order_by(db.desc(Testimonial.created_at)).limit(3).all()
    return render_template('index.html', featured_items=featured_items, testimonials=testimonials)

@app.route('/gallery')
def gallery():
    category = request.args.get('category', 'all')
    query = GalleryItem.query.filter_by(category=category) if category != 'all' else GalleryItem.query
    gallery_items = query.order_by(db.desc(GalleryItem.created_at)).all()
    return render_template('gallery.html', gallery_items=gallery_items, current_category=category)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            event_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date() if request.form['date'] else None
            booking = Booking(
                name=request.form['name'],
                email=request.form['email'],
                phone=request.form['phone'],
                service_type=request.form['service'],
                event_date=event_date,
                message=request.form['message']
            )
            db.session.add(booking)
            db.session.commit()
            send_booking_confirmation(booking)
            flash('Booking request submitted successfully!', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Booking error: {str(e)}")
            flash('Error processing your request', 'danger')
    return render_template('contact.html')

# Helper functions
def send_booking_confirmation(booking):
    try:
        msg = Message(
            subject="Booking Confirmation - Everlight Photography",
            recipients=[booking.email],
            body=f"""Dear {booking.name},
            
Thank you for your booking request for {booking.service_type} photography.
We'll contact you soon to confirm details.

Booking Details:
- Service: {booking.service_type}
- Contact: {booking.phone}
{'Event Date: ' + booking.event_date.strftime('%B %d, %Y') if booking.event_date else ''}

Best regards,
Everlight Photography Team
"""
        )
        mail.send(msg)
        logger.info(f"Sent confirmation to {booking.email}")
    except Exception as e:
        logger.error(f"Email error: {str(e)}")

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)