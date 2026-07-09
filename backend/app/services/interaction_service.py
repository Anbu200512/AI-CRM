from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from app.models.interaction import Interaction
from app.models.hcp import HCP
from app.schemas.interaction import InteractionCreate, InteractionUpdate


def create_interaction(db: Session, data: InteractionCreate, user_id: int) -> Interaction:
    hcp_id = data.hcp_id
    if not hcp_id and data.doctor_name:
        hcp = db.query(HCP).filter(HCP.doctor_name.ilike(f"%{data.doctor_name}%")).first()
        if not hcp:
            hcp = HCP(doctor_name=data.doctor_name, hospital=data.hospital, speciality=data.speciality)
            db.add(hcp)
            db.flush()
        hcp_id = hcp.id

    interaction = Interaction(
        hcp_id=hcp_id,
        summary=data.summary,
        discussion=data.discussion,
        products=data.products,
        competitors=data.competitors,
        sentiment=data.sentiment,
        interest_level=data.interest_level,
        interaction_date=data.interaction_date,
        follow_up_date=data.follow_up_date,
        duration=data.duration,
        interaction_type=data.interaction_type,
        created_by=user_id,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def get_interactions(db: Session, user_id: int, page: int = 1, page_size: int = 10, search: Optional[str] = None, sort_by: str = "created_at", sort_order: str = "desc") -> Dict[str, Any]:
    query = db.query(Interaction).filter(Interaction.created_by == user_id)
    if search:
        query = query.join(HCP, Interaction.hcp_id == HCP.id, isouter=True).filter(
            HCP.doctor_name.ilike(f"%{search}%") | Interaction.summary.ilike(f"%{search}%") | Interaction.products.ilike(f"%{search}%")
        )
    sort_col = getattr(Interaction, sort_by, Interaction.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    result = []
    for item in items:
        d = item.__dict__.copy()
        if item.hcp_id:
            hcp = db.query(HCP).filter(HCP.id == item.hcp_id).first()
            if hcp:
                d["doctor_name"] = hcp.doctor_name
                d["hospital"] = hcp.hospital
        result.append(d)
    return {"total": total, "page": page, "page_size": page_size, "data": result}


def get_interaction(db: Session, interaction_id: int, user_id: int) -> Optional[Dict]:
    item = db.query(Interaction).filter(Interaction.id == interaction_id, Interaction.created_by == user_id).first()
    if not item:
        return None
    d = item.__dict__.copy()
    if item.hcp_id:
        hcp = db.query(HCP).filter(HCP.id == item.hcp_id).first()
        if hcp:
            d["doctor_name"] = hcp.doctor_name
            d["hospital"] = hcp.hospital
    return d


def update_interaction(db: Session, interaction_id: int, data: InteractionUpdate, user_id: int) -> Optional[Interaction]:
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id, Interaction.created_by == user_id).first()
    if not interaction:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(interaction, key, value)
    db.commit()
    db.refresh(interaction)
    return interaction


def delete_interaction(db: Session, interaction_id: int, user_id: int) -> bool:
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id, Interaction.created_by == user_id).first()
    if not interaction:
        return False
    db.delete(interaction)
    db.commit()
    return True


def get_dashboard_data(db: Session, user_id: int) -> Dict[str, Any]:
    today = date.today()
    seven_days_ago = today - timedelta(days=7)
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    total_hcps = db.query(Interaction.hcp_id).filter(
        Interaction.created_by == user_id,
        Interaction.hcp_id.isnot(None)
    ).distinct().count()

    interactions_today = db.query(Interaction).filter(
        Interaction.created_by == user_id,
        func.date(Interaction.created_at) == today
    ).count()

    pending_followups = db.query(Interaction).filter(
        Interaction.created_by == user_id,
        Interaction.follow_up_date >= today
    ).count()

    weekly_meetings = db.query(Interaction).filter(
        Interaction.created_by == user_id,
        Interaction.created_at >= seven_days_ago
    ).count()

    weekly_activity_raw = (
        db.query(
            func.date(Interaction.created_at).label("day"),
            func.count(Interaction.id).label("count")
        )
        .filter(
            Interaction.created_by == user_id,
            Interaction.created_at >= seven_days_ago
        )
        .group_by(func.date(Interaction.created_at))
        .order_by(func.date(Interaction.created_at))
        .all()
    )
    activity_by_date = {str(row.day): row.count for row in weekly_activity_raw}
    weekly_activity = []
    for i in range(7):
        day = today - timedelta(days=6 - i)
        day_str = str(day)
        weekly_activity.append({
            "day": weekday_names[day.weekday()],
            "date": day_str,
            "count": activity_by_date.get(day_str, 0),
        })

    recent = (
        db.query(Interaction, HCP.doctor_name, HCP.hospital)
        .join(HCP, Interaction.hcp_id == HCP.id, isouter=True)
        .filter(Interaction.created_by == user_id)
        .order_by(Interaction.created_at.desc())
        .limit(10)
        .all()
    )
    recent_activities = []
    for r in recent:
        created = r.Interaction.created_at
        recent_activities.append({
            "id": r.Interaction.id,
            "doctor_name": r.doctor_name,
            "interaction_type": r.Interaction.interaction_type,
            "hospital": r.hospital,
            "date": str(created.date()) if created else None,
            "time": created.strftime("%I:%M %p") if created else None,
        })

    upcoming = (
        db.query(Interaction, HCP.doctor_name)
        .join(HCP, Interaction.hcp_id == HCP.id, isouter=True)
        .filter(Interaction.created_by == user_id, Interaction.follow_up_date >= today)
        .order_by(Interaction.follow_up_date.asc())
        .limit(5)
        .all()
    )
    upcoming_followups = [
        {"id": u.Interaction.id, "doctor_name": u.doctor_name, "follow_up_date": u.Interaction.follow_up_date, "interest_level": u.Interaction.interest_level}
        for u in upcoming
    ]

    return {
        "total_hcps": total_hcps,
        "interactions_today": interactions_today,
        "pending_followups": pending_followups,
        "weekly_meetings": weekly_meetings,
        "weekly_activity": weekly_activity,
        "recent_activities": recent_activities,
        "upcoming_followups": upcoming_followups,
    }

