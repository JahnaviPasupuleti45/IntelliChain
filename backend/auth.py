from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database import User, db


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth-token")


def create_token(user):
    return _serializer().dumps({"user_id": user.id})


def login_required(view):
    """Allow the request only if it has a valid 'Authorization: Bearer <token>' header."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Login required"}), 401
        try:
            data = _serializer().loads(
                header[len("Bearer "):], max_age=current_app.config["TOKEN_MAX_AGE_SECONDS"]
            )
        except SignatureExpired:
            return jsonify({"error": "Session expired, please log in again"}), 401
        except BadSignature:
            return jsonify({"error": "Invalid token"}), 401

        user = db.session.get(User, data["user_id"])
        if user is None:
            return jsonify({"error": "User not found"}), 401
        g.user = user
        return view(*args, **kwargs)

    return wrapper


def device_key_required(view):
    """IoT devices authenticate with a shared key in the X-API-Key header."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-API-Key") != current_app.config["DEVICE_API_KEY"]:
            return jsonify({"error": "Invalid device key"}), 401
        return view(*args, **kwargs)

    return wrapper
