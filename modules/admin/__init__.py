"""
ERA: Event Resource & Administration System
Admin Module Blueprint
"""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__, template_folder="../../templates")

from modules.admin import routes  # noqa: F401, E402
