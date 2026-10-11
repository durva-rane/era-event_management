from flask import Response, abort, render_template, request, session

from core.decorators import login_required
from core.errors import AppError
from modules.reports import reports_bp
from modules.reports import services


@reports_bp.get("/reports")
@login_required
def reports_page():
    role = session.get("user_role")
    allowed = services.allowed_reports(role)
    if not allowed: abort(403)
    selected = request.args.get("type", allowed[0])
    if selected not in allowed: abort(403)
    try:
        result = services.report(session["user_id"], role, selected, request.args)
        return render_template("reports/index.html", result=result, role=role, report_types=[(key, services.REPORTS[key]) for key in allowed], events=services.filter_events(session["user_id"], role, request.args), vendors=services.filter_vendors(session["user_id"], role, request.args))
    except AppError as exc:
        return render_template("errors/error.html", code=exc.status_code, message=exc.message), exc.status_code


@reports_bp.get("/reports/<report_type>/export.csv")
@login_required
def reports_csv(report_type):
    try: result = services.report(session["user_id"], session.get("user_role"), report_type, request.args)
    except AppError as exc: return str(exc.message), exc.status_code
    return Response(services.csv_export(result), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=era-{report_type}-report.csv"})


@reports_bp.get("/reports/<report_type>/export.pdf")
@login_required
def reports_pdf(report_type):
    try: result = services.report(session["user_id"], session.get("user_role"), report_type, request.args)
    except AppError as exc: return str(exc.message), exc.status_code
    return Response(services.pdf_export(result), mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename=era-{report_type}-report.pdf"})
