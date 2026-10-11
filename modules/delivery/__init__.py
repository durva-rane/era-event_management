from flask import Blueprint

delivery_bp = Blueprint("delivery", __name__)

from modules.delivery import routes  # noqa: E402,F401
