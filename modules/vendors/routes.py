from flask import jsonify, render_template, request, session
from core.decorators import login_required, role_required
from core.errors import AppError
from modules.vendors import vendors_bp
from modules.vendors import services
from modules.vendors.recommendation_service import recommend_vendors


def _data(): return request.get_json(silent=True) or request.form.to_dict()


def _error(exc):
    body={"success":False,"message":getattr(exc,"message",str(exc))}
    if getattr(exc,"payload",None): body.update(exc.payload)
    return jsonify(body),getattr(exc,"status_code",400)


@vendors_bp.get("/api/vendors")
def browse():
    try: return jsonify(success=True,vendors=services.browse_vendors(request.args))
    except (AppError,ValueError) as exc: return _error(exc)


@vendors_bp.get("/api/vendors/compare")
def compare():
    try: return jsonify(success=True,vendors=services.compare_vendors(request.args.getlist("id") or request.args.get("ids","").split(",")))
    except AppError as exc: return _error(exc)


@vendors_bp.get("/api/vendors/recommendations")
@role_required("client","organizer")
def recommendations():
    try: return jsonify(success=True,vendors=recommend_vendors(request.args))
    except (AppError,ValueError) as exc: return _error(exc)


@vendors_bp.get("/api/vendors/<int:vendor_id>")
def profile_get(vendor_id):
    try:
        profile=services.vendor_profile(vendor_id); profile["services"]=services.list_services(vendor_id)
        return jsonify(success=True,vendor=profile)
    except AppError as exc: return _error(exc)


@vendors_bp.route("/api/vendors/me",methods=["GET","PUT","PATCH"])
@role_required("vendor")
def profile_me():
    if request.method=="GET": return profile_get(session["user_id"])
    try: services.save_profile(session["user_id"],_data()); return jsonify(success=True,message="Vendor profile updated.")
    except AppError as exc: return _error(exc)


@vendors_bp.get("/api/vendors/<int:vendor_id>/services")
def services_list(vendor_id):
    try: return jsonify(success=True,services=services.list_services(vendor_id))
    except AppError as exc: return _error(exc)


@vendors_bp.route("/api/vendors/me/services",methods=["POST"])
@role_required("vendor")
def service_create():
    try: return jsonify(success=True,service_id=services.service_action(session["user_id"],None,_data())),201
    except AppError as exc: return _error(exc)


@vendors_bp.route("/api/vendors/me/services/<int:service_id>",methods=["PUT","PATCH","DELETE"])
@role_required("vendor")
def service_edit(service_id):
    try:
        services.service_action(session["user_id"],service_id,_data(),request.method=="DELETE")
        return jsonify(success=True)
    except AppError as exc: return _error(exc)


@vendors_bp.get("/api/vendors/<int:vendor_id>/availability")
def availability_list(vendor_id):
    try: return jsonify(success=True,availability=services.list_availability(vendor_id))
    except AppError as exc: return _error(exc)


@vendors_bp.route("/api/vendors/me/availability",methods=["POST"])
@role_required("vendor")
def availability_create():
    try: return jsonify(success=True,slot_id=services.availability_action(session["user_id"],None,_data())),201
    except AppError as exc: return _error(exc)


@vendors_bp.route("/api/vendors/me/availability/<int:slot_id>",methods=["PUT","PATCH","DELETE"])
@role_required("vendor")
def availability_edit(slot_id):
    try:
        services.availability_action(session["user_id"],slot_id,_data(),request.method=="DELETE")
        return jsonify(success=True)
    except AppError as exc: return _error(exc)


@vendors_bp.route("/api/vendor-bookings",methods=["GET","POST"])
@login_required
def bookings():
    if request.method=="GET": return jsonify(success=True,bookings=services.list_bookings(session["user_id"],session["user_role"]))
    if session.get("user_role") not in ("client","organizer","admin"): return jsonify(success=False,message="Only clients and organizers can request vendor bookings."),403
    data=_data()
    try: return jsonify(success=True,booking_id=services.create_booking(session["user_id"],session["user_role"],data.get("event_id"),data)),201
    except (AppError,ValueError) as exc: return _error(exc)


@vendors_bp.get("/api/vendor-bookings/requests")
@role_required("vendor")
def booking_requests(): return jsonify(success=True,requests=services.vendor_requests(session["user_id"]))


@vendors_bp.get("/vendor/bookings/requests")
@role_required("vendor")
def booking_requests_page(): return render_template("vendors/requests.html",requests=services.vendor_requests(session["user_id"]))


@vendors_bp.post("/api/vendor-bookings/<int:booking_id>/respond")
@role_required("vendor")
def booking_respond(booking_id):
    try: return jsonify(success=True,**services.respond_booking(session["user_id"],booking_id,_data().get("decision")))
    except AppError as exc: return _error(exc)


@vendors_bp.post("/api/vendor-bookings/<int:booking_id>/cancel")
@login_required
def booking_cancel(booking_id):
    try: services.cancel_booking(session["user_id"],session["user_role"],booking_id,_data().get("reason")); return jsonify(success=True)
    except AppError as exc: return _error(exc)


@vendors_bp.post("/api/vendor-bookings/<int:booking_id>/complete")
@role_required("vendor")
def booking_complete(booking_id):
    try: services.complete_booking(session["user_id"],booking_id); return jsonify(success=True)
    except AppError as exc: return _error(exc)


@vendors_bp.post("/api/vendor-bookings/<int:booking_id>/reviews")
@role_required("client","organizer")
def review_create(booking_id):
    try: return jsonify(success=True,review_id=services.create_review(session["user_id"],session["user_role"],booking_id,_data())),201
    except AppError as exc: return _error(exc)


@vendors_bp.route("/api/events/<int:event_id>/messages",methods=["GET","POST"])
@role_required("client","organizer")
def event_chat(event_id):
    try:
        messages=services.event_messages(session["user_id"],session["user_role"],event_id,request.args.get("after_id",0),_data().get("message") if request.method=="POST" else None)
        return jsonify(success=True,messages=messages)
    except (AppError,ValueError) as exc: return _error(exc)
