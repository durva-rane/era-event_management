from flask import Blueprint

events_bp = Blueprint("events", __name__)

from modules.events import routes  # noqa: E402,F401
