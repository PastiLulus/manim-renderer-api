from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from .routes.video_rendering import video_rendering_bp
import os

def create_app():
    app = Flask(__name__, static_folder="public", static_url_path="/public")

    load_dotenv()

    app.register_blueprint(video_rendering_bp)

    CORS(app)
    
    @app.route("/")
    def index():
        print("Manim API")
        return "Manim API"
    
    @app.route("/public/videos/<path:filename>")
    def serve_video(filename):
        return send_from_directory(os.path.join(app.static_folder, "videos"), filename)

    return app
