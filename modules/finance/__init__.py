from flask import Blueprint

finance_bp = Blueprint("finance", __name__)

from modules.finance import routes  # noqa: E402,F401
