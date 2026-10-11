"""
ERA: Event Resource & Administration System
Custom Domain Exceptions & Global Error Handlers
"""

from flask import jsonify, render_template, request


class AppError(Exception):
    """Base application exception."""
    status_code = 500

    def __init__(self, message: str, status_code: int = None, payload=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload


class ValidationError(AppError):
    status_code = 400


class AuthenticationError(AppError):
    status_code = 401


class AuthorizationError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


def register_error_handlers(app):
    """Registers standard application error handlers."""

    def is_api_request():
        return (
            request.path.startswith("/api/")
            or request.headers.get("Accept") == "application/json"
            or request.is_json
        )

    @app.errorhandler(AppError)
    def handle_app_error(err):
        if is_api_request():
            return jsonify(success=False, message=err.message), err.status_code
        return render_template("errors/error.html", code=err.status_code, message=err.message), err.status_code

    @app.errorhandler(400)
    def bad_request(e):
        if is_api_request():
            return jsonify(success=False, message="Invalid request parameters."), 400
        return render_template("errors/error.html", code=400, message="Bad Request"), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if is_api_request():
            return jsonify(success=False, message="Authentication required."), 401
        return render_template("errors/error.html", code=401, message="Please log in to continue."), 401

    @app.errorhandler(403)
    def forbidden(e):
        if is_api_request():
            return jsonify(success=False, message="Access forbidden. Insufficient permissions."), 403
        return render_template("errors/error.html", code=403, message="Access Denied"), 403

    @app.errorhandler(404)
    def not_found(e):
        if is_api_request():
            return jsonify(success=False, message="Requested resource not found."), 404
        return render_template("errors/error.html", code=404, message="Page Not Found"), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal server error: {e}")
        if is_api_request():
            return jsonify(success=False, message="An internal server error occurred. Please try again later."), 500
        return render_template("errors/error.html", code=500, message="Server Error. Please try again later."), 500
