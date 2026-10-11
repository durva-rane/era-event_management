from flask import render_template, session

from core.decorators import login_required
from modules.dashboard import dashboard_bp
from modules.dashboard.services import dashboard


@dashboard_bp.get("/dashboard/overview")
@login_required
def dashboard_page():
    role = session.get("user_role")
    return render_template("dashboard/overview.html", role=role, data=dashboard(session["user_id"], role, session.get("user_email", "")))
