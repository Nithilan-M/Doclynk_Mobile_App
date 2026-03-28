from flask import Flask, jsonify
from dotenv import load_dotenv
import os

from api_routes import api_bp
from security import add_security_headers

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret")

# Keep session/security defaults even for API-only mode.
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600

# Register REST API blueprint.
app.register_blueprint(api_bp)


@app.after_request
def apply_security_headers(response):
    return add_security_headers(response)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "message": "DocLynk API is running"}), 200


@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "message": "DocLynk backend API",
            "health": "/health",
            "api_base": "/api",
        }
    ), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_ENV", "development") != "production",
    )
