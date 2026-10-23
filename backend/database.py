from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(15), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "fullname": self.fullname,
            "email": self.email,
            "phone": self.phone,
        }


class ShipmentReading(db.Model):
    """One IoT sensor reading for a shipment, with the model's risk assessment."""

    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.String(50), nullable=False, index=True)
    product_type = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    delay_hours = db.Column(db.Float, nullable=False)
    risk = db.Column(db.String(10), nullable=False)
    risk_probability = db.Column(db.Float, nullable=False)
    report = db.Column(db.Text, nullable=False)
    report_source = db.Column(db.String(10), nullable=False)  # "llm" or "template"
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "shipment_id": self.shipment_id,
            "product_type": self.product_type,
            "location": self.location,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "delay_hours": self.delay_hours,
            "risk": self.risk,
            "risk_probability": self.risk_probability,
            "report": self.report,
            "report_source": self.report_source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
