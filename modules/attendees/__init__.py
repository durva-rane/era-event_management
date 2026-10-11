from flask import Blueprint

attendees_bp = Blueprint("attendees", __name__, template_folder="../../templates")

from modules.attendees import routes  # noqa: E402,F401
