from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail, Message
from datetime import datetime
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env
load_dotenv()

app = Flask(__name__, template_folder='templates')

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-fallback-secret-key')

# ✅ Use correct URI with encoded password
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://root:Bindu%40134366@localhost/everlight'  # @ → %40
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration (optional)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================
# Database Models
# ==============================

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    event_date = db.Column(db.Date, nullable=True)
    message = db.Column(db.Text, nullable=True)
    special_requests = db.Column(db.Text, nullable=True)  # ✅ Added this field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')

    def __repr__(self):
        return f'<Booking {self.name}>'

# ==============================
# Routes
# ==============================

@app.route('/')
def home():
    return render_template('index.html')

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
                message=request.form['message'],
                special_requests=request.form.get('special_requests')  # ✅ Save the field
            )
            db.session.add(booking)
            db.session.commit()

            send_booking_confirmation(booking)
            flash('Booking submitted successfully!', 'success')
            return redirect(url_for('contact'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Booking error: {e}")
            flash('Error occurred during booking.', 'danger')

    return render_template('contact.html')

# ==============================
# Admin Route: View All Bookings
# ==============================
@app.route('/bookings')
def view_bookings():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('bookings.html', bookings=bookings)

# ==============================
# Helper
# ==============================

def send_booking_confirmation(booking):
    try:
        msg = Message(
            subject="Booking Confirmation - Everlight Photography",
            recipients=[booking.email],
            body=f"""
Hello {booking.name},

Thank you for your booking request for {booking.service_type}.
We will contact you shortly.

Special Requests: {booking.special_requests or 'None'}

Regards,
Everlight Photography
            """
        )
        mail.send(msg)
        logger.info(f"Email sent to {booking.email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

# ==============================
# Run
# ==============================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("✅ Database connected and table created.")
    app.run(debug=True)
