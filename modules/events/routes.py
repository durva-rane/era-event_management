from flask import jsonify, request, session, Response
from core.decorators import login_required, role_required
from core.errors import AppError
from modules.events import events_bp
from modules.events.services import (change_event_status, event_details, list_events,
    save_event, save_venue, list_owned_venues, search_venues, schedule_action)


def _data():
    return request.get_json(silent=True) or request.form.to_dict()


@events_bp.get("/api/venues")
def venues_search():
    try:
        return jsonify(success=True,venues=search_venues(request.args))
    except (ValueError, AppError) as exc:
        return jsonify(success=False,message=getattr(exc,"message",str(exc))),getattr(exc,"status_code",400)


@events_bp.route("/api/venues/mine",methods=["GET"])
@role_required("venue_owner")
def venues_mine():
    return jsonify(success=True,venues=list_owned_venues(session["user_id"]))


@events_bp.route("/api/venues",methods=["POST"])
@role_required("venue_owner")
def venue_create():
    try:
        venue_id=save_venue(session["user_id"],_data())
        return jsonify(success=True,venue_id=venue_id,status="pending"),201
    except AppError as exc:
        return jsonify(success=False,message=exc.message),exc.status_code


@events_bp.route("/api/venues/<int:venue_id>",methods=["PUT","PATCH"])
@role_required("venue_owner")
def venue_edit(venue_id):
    try:
        save_venue(session["user_id"],_data(),venue_id)
        return jsonify(success=True,venue_id=venue_id,status="pending")
    except AppError as exc:
        return jsonify(success=False,message=exc.message),exc.status_code


@events_bp.route("/api/events/calendar",methods=["GET"])
@events_bp.route("/api/events",methods=["GET"])
@login_required
def events_list():
    return jsonify(success=True,events=list_events(session["user_id"],session["user_role"],request.args))


@events_bp.route("/api/events",methods=["POST"])
@role_required("client","organizer")
def event_create():
    try:
        event_id=save_event(session["user_id"],session["user_role"],_data())
        return jsonify(success=True,event_id=event_id),201
    except AppError as exc:
        result={"success":False,"message":exc.message}
        if exc.payload: result.update(exc.payload)
        return jsonify(result),exc.status_code


@events_bp.route("/api/events/<int:event_id>",methods=["GET"])
@login_required
def event_get(event_id):
    try: return jsonify(success=True,event=event_details(session["user_id"],session["user_role"],event_id))
    except AppError as exc: return jsonify(success=False,message=exc.message),exc.status_code


@events_bp.route("/api/events/<int:event_id>",methods=["PUT","PATCH"])
@role_required("client","organizer")
def event_edit(event_id):
    try:
        save_event(session["user_id"],session["user_role"],_data(),event_id)
        return jsonify(success=True,event_id=event_id)
    except AppError as exc:
        result={"success":False,"message":exc.message}
        if exc.payload: result.update(exc.payload)
        return jsonify(result),exc.status_code


@events_bp.route("/api/events/<int:event_id>/cancel",methods=["POST"])
@role_required("client","organizer")
def event_cancel(event_id):
    try:
        change_event_status(session["user_id"],session["user_role"],event_id,"cancelled")
        return jsonify(success=True,message="Event cancelled.")
    except AppError as exc: return jsonify(success=False,message=exc.message),exc.status_code


@events_bp.route("/api/events/<int:event_id>/schedule",methods=["POST"])
@role_required("client","organizer")
def schedule_create(event_id):
    try: return jsonify(success=True,item_id=schedule_action(session["user_id"],session["user_role"],event_id,None,_data())),201
    except AppError as exc: return jsonify(success=False,message=exc.message),exc.status_code


@events_bp.route("/api/events/<int:event_id>/schedule/<int:item_id>",methods=["PUT","PATCH","DELETE"])
@role_required("client","organizer")
def schedule_edit(event_id,item_id):
    try:
        schedule_action(session["user_id"],session["user_role"],event_id,item_id,_data(),request.method=="DELETE")
        return jsonify(success=True)
    except AppError as exc: return jsonify(success=False,message=exc.message),exc.status_code


@events_bp.get("/api/events/<int:event_id>/pdf")
@login_required
def event_pdf(event_id):
    try: event=event_details(session["user_id"],session["user_role"],event_id)
    except AppError as exc: return jsonify(success=False,message=exc.message),exc.status_code
    # A compact standards-compliant PDF, with escaped text and a single page.
    lines=[f"Event: {event['name']}",f"Category: {event['category']}",f"Date: {event['event_date']}",f"Time: {event['start_time']} - {event['end_time']}",f"Expected attendees: {event['expected_attendees']}",f"Venue: {event.get('venue_name') or 'Not selected'}",f"Location: {event.get('venue_location') or 'Not specified'}",f"Status: {event['status']}",f"Description: {event.get('description') or ''}","Schedule:"]
    lines += [f"{item['start_time']} - {item['end_time']}  {item['title']}" for item in event["schedule"]]
    esc=lambda s: str(s).encode("ascii","replace").decode().replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
    stream="BT /F1 11 Tf 50 790 Td 14 TL "+" ".join(f"({esc(line)}) Tj T*" for line in lines)+" ET"
    objects=["<< /Type /Catalog /Pages 2 0 R >>","<< /Type /Pages /Kids [3 0 R] /Count 1 >>","<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>","<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream"]
    pdf="%PDF-1.4\n"; offsets=[0]
    for i,obj in enumerate(objects,1): offsets.append(len(pdf.encode())); pdf+=f"{i} 0 obj\n{obj}\nendobj\n"
    xref=len(pdf.encode()); pdf+="xref\n0 6\n0000000000 65535 f \n"+"".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])+f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return Response(pdf,mimetype="application/pdf",headers={"Content-Disposition":f"attachment; filename=event-{event_id}.pdf"})
