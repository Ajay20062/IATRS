from flask import Flask
from flask_cors import CORS

from .config import load_app_config
from .routes import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(load_app_config())

    CORS(app)
    app.register_blueprint(api_bp)

    return app
