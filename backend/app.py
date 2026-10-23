import os

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from sqlalchemy import func

import assistant
import llm
from auth import create_token, device_key_required, login_required
from config import Config
from database import ShipmentReading, User, db
from reports import build_report
from risk_model import PRODUCT_TYPES, predict_risk


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)

    os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)
    db.init_app(app)
    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def bad_request(message):
    return jsonify({"error": message}), 400


def register_routes(app):

    # ---------------- HEALTH ----------------
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "llm_provider": llm.provider()})

    # ---------------- AUTH ----------------
    @app.route("/api/register", methods=["POST"])
    def register():
        data = request.get_json(silent=True) or {}
        fullname = (data.get("fullname") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        phone = (data.get("phone") or "").strip()

        if not all([fullname, email, password, phone]):
            return bad_request("All fields are required")
        if len(password) < 6:
            return bad_request("Password must be at least 6 characters")
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered"}), 409

        user = User(fullname=fullname, email=email, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "Registration successful"}), 201

    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid email or password"}), 401
        return jsonify({"token": create_token(user), "user": user.to_dict()})

    @app.route("/api/me")
    @login_required
    def me():
        return jsonify(g.user.to_dict())

    # ---------------- IOT INGESTION ----------------
    @app.route("/api/sensor", methods=["POST"])
    @device_key_required
    def receive_sensor_data():
        data = request.get_json(silent=True) or {}

        shipment_id = (data.get("shipment_id") or "").strip()
        location = (data.get("location") or "").strip()
        product_type = (data.get("product_type") or "general").strip().lower()
        if not shipment_id or not location:
            return bad_request("shipment_id and location are required")
        if product_type not in PRODUCT_TYPES:
            return bad_request(f"product_type must be one of {PRODUCT_TYPES}")
        try:
            temperature = float(data["temperature"])
            humidity = float(data["humidity"])
            delay_hours = float(data.get("delay_hours", 0))
        except (KeyError, TypeError, ValueError):
            return bad_request("temperature, humidity and delay_hours must be numbers")

        risk, probability = predict_risk(product_type, temperature, humidity, delay_hours)
        reading = {
            "shipment_id": shipment_id,
            "product_type": product_type,
            "location": location,
            "temperature": temperature,
            "humidity": humidity,
            "delay_hours": delay_hours,
            "risk": risk,
            "risk_probability": probability,
        }
        report, report_source = build_report(reading)

        entry = ShipmentReading(**reading, report=report, report_source=report_source)
        db.session.add(entry)
        db.session.commit()
        return jsonify(entry.to_dict()), 201

    # ---------------- DASHBOARD ----------------
    @app.route("/api/dashboard")
    @login_required
    def dashboard():
        latest = sorted(assistant.latest_readings(), key=lambda r: r.id, reverse=True)
        counts = {level: sum(r.risk == level for r in latest) for level in ("LOW", "MEDIUM", "HIGH")}
        return jsonify({
            "summary": {"total_shipments": len(latest), **counts},
            "shipments": [r.to_dict() for r in latest],
        })

    @app.route("/api/shipments/<shipment_id>")
    @login_required
    def shipment_history(shipment_id):
        readings = (
            ShipmentReading.query.filter(func.upper(ShipmentReading.shipment_id) == shipment_id.upper())
            .order_by(ShipmentReading.id.desc())
            .all()
        )
        if not readings:
            return jsonify({"error": f"No readings found for {shipment_id}"}), 404
        return jsonify({"shipment_id": readings[0].shipment_id, "readings": [r.to_dict() for r in readings]})

    # ---------------- OPS COPILOT (RAG) ----------------
    @app.route("/api/assistant", methods=["POST"])
    @login_required
    def ask_assistant():
        question = ((request.get_json(silent=True) or {}).get("question") or "").strip()
        if not question:
            return bad_request("question is required")
        if len(question) > 500:
            return bad_request("question must be 500 characters or fewer")
        return jsonify(assistant.answer(question))


if __name__ == "__main__":
    create_app().run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")))
