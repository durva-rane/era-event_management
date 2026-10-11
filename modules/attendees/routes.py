from flask import jsonify, render_template, request, session, url_for
from core.decorators import login_required, role_required
from core.errors import AppError
from modules.attendees import attendees_bp
from modules.attendees import services


def _data(): return request.get_json(silent=True) or request.form.to_dict()


def _error(exc): return jsonify(success=False,message=getattr(exc,"message",str(exc))),getattr(exc,"status_code",400)


@attendees_bp.route("/events/<int:event_id>/attendees",methods=["GET"])
@role_required("organizer")
def attendee_management_page(event_id):
    try:
        guests=services.guest_list(session["user_id"],session["user_role"],event_id,request.args)
        summary=services.live_summary(session["user_id"],session["user_role"],event_id)
        return render_template("attendees/manage.html",guests=guests,summary=summary,event_id=event_id)
    except AppError as exc: return render_template("errors/error.html",code=exc.status_code,message=exc.message),exc.status_code


@attendees_bp.route("/api/events/<int:event_id>/attendees",methods=["GET","POST"])
@role_required("organizer")
def attendee_collection(event_id):
    try:
        if request.method=="GET": return jsonify(success=True,attendees=services.guest_list(session["user_id"],session["user_role"],event_id,request.args))
        attendee_id,token=services.add_attendee(session["user_id"],session["user_role"],event_id,_data())
        return jsonify(success=True,attendee_id=attendee_id,rsvp_path=url_for("attendees.rsvp_page",token=token)),201
    except AppError as exc: return _error(exc)


@attendees_bp.route("/api/events/<int:event_id>/attendees/import",methods=["POST"])
@role_required("organizer")
def attendee_import(event_id):
    uploaded=request.files.get("file")
    if not uploaded: return jsonify(success=False,message="CSV file is required."),400
    try: return jsonify(success=True,report=services.import_csv(session["user_id"],session["user_role"],event_id,uploaded.stream)),200
    except AppError as exc: return _error(exc)


@attendees_bp.route("/api/events/<int:event_id>/attendees/<int:attendee_id>",methods=["PUT","PATCH","DELETE"])
@role_required("organizer")
def attendee_item(event_id,attendee_id):
    try:
        if request.method=="DELETE": services.remove_attendee(session["user_id"],session["user_role"],event_id,attendee_id)
        else: services.edit_attendee(session["user_id"],session["user_role"],event_id,attendee_id,_data())
        return jsonify(success=True)
    except AppError as exc: return _error(exc)


@attendees_bp.get("/api/events/<int:event_id>/attendees/summary")
@role_required("organizer")
def attendee_summary(event_id):
    try: return jsonify(success=True,summary=services.live_summary(session["user_id"],session["user_role"],event_id))
    except AppError as exc: return _error(exc)


@attendees_bp.post("/api/events/<int:event_id>/attendees/<int:attendee_id>/check-in")
@role_required("organizer")
def attendee_checkin(event_id,attendee_id):
    try: return jsonify(success=True,message=services.check_in(session["user_id"],session["user_role"],event_id,attendee_id))
    except AppError as exc: return _error(exc)


@attendees_bp.post("/api/events/<int:event_id>/attendees/<int:attendee_id>/check-out")
@role_required("organizer")
def attendee_checkout(event_id,attendee_id):
    try: return jsonify(success=True,message=services.check_in(session["user_id"],session["user_role"],event_id,attendee_id,True))
    except AppError as exc: return _error(exc)


@attendees_bp.route("/rsvp/<token>",methods=["GET","POST"])
def rsvp_page(token):
    try:
        if request.method=="POST": result=services.submit_rsvp(token,_data().get("status")); return render_template("attendees/rsvp.html",event=services.rsvp_page_data(token),saved=result["status"])
        return render_template("attendees/rsvp.html",event=services.rsvp_page_data(token),saved=None)
    except AppError as exc: return render_template("errors/error.html",code=exc.status_code,message=exc.message),exc.status_code


@attendees_bp.route("/my/invitations",methods=["GET"])
@role_required("attendee")
def my_invitations():
    invitations=services.attendee_invitations(session.get("user_email",""),request.args)
    return render_template("attendees/invitations.html",invitations=invitations)


@attendees_bp.get("/api/my/invitations")
@role_required("attendee")
def my_invitations_api(): return jsonify(success=True,invitations=services.attendee_invitations(session.get("user_email",""),request.args))
