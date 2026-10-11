"""
ERA: Event Resource & Administration System
Auth Module Blueprint
"""

from flask import Blueprint

auth_bp = Blueprint("auth", __name__, template_folder="../../templates")

from modules.auth import routes  # noqa: F401, E402
