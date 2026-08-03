"""
REST route blueprints for the web simulation backend.

Each concern (status, camera, recognition, game) lives in its own blueprint so
the previous single 2000-line ``app.py`` is now a small composition root plus
these focused modules. Shared mutable state (``game_state``, the recognizer,
camera selection, the STM32 client) is owned by ``web_simulation.app`` and is
reached through that module object so the routes never hold stale copies.
"""

from web_simulation.routes import camera, game, recognition, status


def register_routes(app):
    """Attach every blueprint to the Flask application."""
    app.register_blueprint(status.bp)
    app.register_blueprint(camera.bp)
    app.register_blueprint(recognition.bp)
    app.register_blueprint(game.bp)
