from flask import jsonify, request, session, Response
from core.decorators import login_required, role_required
from core.errors import AppError
from modules.finance import finance_bp, services


def _data(): return request.get_json(silent=True) or request.form.to_dict()


def _fail(exc): return jsonify(success=False,message=getattr(exc,"message",str(exc))),getattr(exc,"status_code",400)


@finance_bp.route("/api/events/<int:event_id>/budget",methods=["GET","POST","PUT"])
@role_required("client","organizer")
def budget(event_id):
    try:
        if request.method=="GET": return jsonify(success=True,budget=services.budget_summary(session["user_id"],session["user_role"],event_id))
        data=_data(); services.set_budget(session["user_id"],session["user_role"],event_id,data.get("total_amount"))
        return jsonify(success=True,budget=services.budget_summary(session["user_id"],session["user_role"],event_id))
    except AppError as exc: return _fail(exc)


@finance_bp.get("/api/events/<int:event_id>/budget/estimate")
@role_required("client","organizer")
def budget_estimate(event_id):
    try: return jsonify(success=True,estimate=services.estimate_event(session["user_id"],session["user_role"],event_id))
    except AppError as exc: return _fail(exc)


@finance_bp.route("/api/events/<int:event_id>/budget/items",methods=["POST"])
@role_required("client","organizer")
def budget_item_create(event_id):
    try: return jsonify(success=True,item_id=services.budget_item_action(session["user_id"],session["user_role"],event_id,None,_data())),201
    except AppError as exc: return _fail(exc)


@finance_bp.route("/api/events/<int:event_id>/budget/items/<int:item_id>",methods=["PUT","PATCH","DELETE"])
@role_required("client","organizer")
def budget_item_edit(event_id,item_id):
    try:
        services.budget_item_action(session["user_id"],session["user_role"],event_id,item_id,_data(),request.method=="DELETE")
        return jsonify(success=True)
    except AppError as exc: return _fail(exc)


@finance_bp.post("/api/bookings/<int:booking_id>/payments")
@login_required
def payment_initiate(booking_id):
    try: return jsonify(success=True,**services.initiate_payment(session["user_id"],session["user_role"],booking_id,_data().get("amount"))),201
    except (AppError,TypeError) as exc: return _fail(exc)


@finance_bp.post("/api/payments/callback")
@finance_bp.post("/api/payments/verify")
@login_required
def payment_verify():
    data=_data()
    try:
        record_id=data.get("payment_record_id")
        result=services.verify_payment(session["user_id"],session["user_role"],int(record_id) if record_id else None,data.get("order_id") or data.get("razorpay_order_id"),data.get("payment_id") or data.get("razorpay_payment_id"),data.get("signature") or data.get("razorpay_signature"))
        return jsonify(success=True,**result)
    except (AppError,TypeError,ValueError) as exc: return _fail(exc)


@finance_bp.get("/api/invoices")
@login_required
def invoices_list(): return jsonify(success=True,invoices=services.list_invoices(session["user_id"],session["user_role"]))


@finance_bp.get("/api/invoices/<int:invoice_id>")
@login_required
def invoice_get(invoice_id):
    try: return jsonify(success=True,invoice=services.invoice_details(session["user_id"],session["user_role"],invoice_id))
    except AppError as exc: return _fail(exc)


@finance_bp.get("/api/invoices/<int:invoice_id>/pdf")
@login_required
def invoice_pdf(invoice_id):
    try: invoice=services.invoice_details(session["user_id"],session["user_role"],invoice_id)
    except AppError as exc: return _fail(exc)
    return Response(services.invoice_pdf(invoice),mimetype="application/pdf",headers={"Content-Disposition":f"attachment; filename={invoice['invoice_no']}.pdf"})
