from flask import Blueprint

vendors_bp = Blueprint("vendors", __name__, template_folder="../../templates")

from modules.vendors import routes  # noqa: E402,F401
