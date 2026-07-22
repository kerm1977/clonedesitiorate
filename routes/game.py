from flask import Blueprint

game_bp = Blueprint('game', __name__)

# Import and register all route modules
from routes.game_main import register_game_routes
from routes.game_rating import register_game_rating_routes
from routes.game_images import register_game_images_routes
from routes.game_favorites import register_game_favorites_routes
from routes.game_survey import register_game_survey_routes
from routes.game_feedback import register_game_feedback_routes
from routes.game_sw import register_game_sw_routes
from routes.game_stories import register_game_stories_routes
from routes.game_chat import register_game_chat_routes

# Register all routes
register_game_routes(game_bp)
register_game_rating_routes(game_bp)
register_game_images_routes(game_bp)
register_game_favorites_routes(game_bp)
register_game_survey_routes(game_bp)
register_game_feedback_routes(game_bp)
register_game_sw_routes(game_bp)
register_game_stories_routes(game_bp)
register_game_chat_routes(game_bp)
