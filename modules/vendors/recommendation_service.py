"""Explainable vendor ranking for an event's type, budget, location and slot."""
from decimal import Decimal, InvalidOperation

from core.db import get_db_cursor


def recommend_vendors(criteria):
    try:
        budget = Decimal(str(criteria.get("budget", "0") or "0"))
    except InvalidOperation:
        budget = Decimal("0")
    query = """SELECT v.user_id,v.business_name,v.service_type,v.description,v.pricing,v.location,
      v.verification_status,COALESCE(r.avg_rating,0) AS average_rating,COALESCE(r.review_count,0) AS review_count,
      COALESCE(s.service_count,0) AS service_count,COALESCE(s.min_price,v.pricing) AS min_service_price
      FROM vendors v LEFT JOIN (SELECT vendor_id,AVG(rating) avg_rating,COUNT(*) review_count FROM reviews GROUP BY vendor_id) r ON r.vendor_id=v.user_id
      LEFT JOIN (SELECT vendor_id,COUNT(*) service_count,MIN(price) min_price FROM vendor_services GROUP BY vendor_id) s ON s.vendor_id=v.user_id
      WHERE v.verification_status='verified'"""
    params=[]
    if criteria.get("service_type") or criteria.get("category"):
        query += " AND v.service_type LIKE %s"; params.append("%"+(criteria.get("service_type") or criteria.get("category"))+"%")
    if criteria.get("location"):
        query += " AND v.location LIKE %s"; params.append("%"+criteria["location"]+"%")
    with get_db_cursor() as (cur,_):
        cur.execute(query,tuple(params)); vendors=cur.fetchall()
        for vendor in vendors:
            score=0; reasons=[]
            if criteria.get("category") and criteria["category"].lower() in vendor["service_type"].lower(): score+=25; reasons.append("event category")
            if criteria.get("service_type") and criteria["service_type"].lower() in vendor["service_type"].lower(): score+=20; reasons.append("service type")
            if budget:
                price=Decimal(str(vendor["min_service_price"] or 0))
                if price <= budget: score+=20; reasons.append("within budget")
                else: score+=max(0,10-float((price-budget)/max(budget,Decimal(1))*10))
            if criteria.get("location") and criteria["location"].lower() in (vendor["location"] or "").lower(): score+=15; reasons.append("location match")
            rating=float(vendor["average_rating"] or 0); score+=min(20,rating*4)
            if rating: reasons.append(f"rated {rating:.1f}/5")
            if criteria.get("date") and criteria.get("start_time") and criteria.get("end_time"):
                cur.execute("SELECT 1 FROM vendor_availability WHERE vendor_id=%s AND date=%s AND start_time<=%s AND end_time>=%s LIMIT 1",(vendor["user_id"],criteria["date"],criteria["start_time"],criteria["end_time"]))
                available=bool(cur.fetchone())
                cur.execute("SELECT 1 FROM bookings WHERE vendor_id=%s AND booking_type='vendor' AND booking_date=%s AND status='confirmed' AND start_time<%s AND end_time>%s LIMIT 1",(vendor["user_id"],criteria["date"],criteria["end_time"],criteria["start_time"]))
                available=available and not bool(cur.fetchone())
                if available: score+=20; reasons.append("available for event slot")
                else: score-=20
            vendor["recommendation_score"]=round(score,2); vendor["recommendation_reasons"]=reasons
        return sorted(vendors,key=lambda item:(-item["recommendation_score"],-float(item["average_rating"] or 0)))
