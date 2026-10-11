from flask import Blueprint

reports_bp = Blueprint("reports", __name__)

from modules.reports import routes  # noqa: E402,F401
