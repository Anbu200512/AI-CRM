from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database.connection import get_db
from app.models.user import User
from app.schemas.interaction import InteractionCreate, InteractionUpdate, InteractionResponse, InteractionListResponse
from app.services.interaction_service import create_interaction, get_interactions, get_interaction, update_interaction, delete_interaction
from app.utils.auth import get_current_user
from fastapi import BackgroundTasks
from app.utils.websocket import manager

router = APIRouter(prefix="/api/interactions", tags=["Interactions"])


@router.post("", response_model=InteractionResponse, status_code=201)
def create(data: InteractionCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interaction = create_interaction(db, data, current_user.id)
    resp = get_interaction(db, interaction.id, current_user.id)
    background_tasks.add_task(manager.broadcast_to_user, current_user.id, {"type": "DASHBOARD_UPDATED"})
    return InteractionResponse(**resp)


@router.get("", response_model=InteractionListResponse)
def list_interactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_interactions(db, current_user.id, page, page_size, search, sort_by, sort_order)


@router.get("/{id}", response_model=InteractionResponse)
def get(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = get_interaction(db, id, current_user.id)
    if not result:
        raise HTTPException(404, "Interaction not found")
    return InteractionResponse(**result)


@router.put("/{id}", response_model=InteractionResponse)
def update(id: int, data: InteractionUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = update_interaction(db, id, data, current_user.id)
    if not result:
        raise HTTPException(404, "Interaction not found")
    resp = get_interaction(db, id, current_user.id)
    background_tasks.add_task(manager.broadcast_to_user, current_user.id, {"type": "DASHBOARD_UPDATED"})
    return InteractionResponse(**resp)


@router.delete("/{id}", status_code=204)
def delete(id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not delete_interaction(db, id, current_user.id):
        raise HTTPException(404, "Interaction not found")
    background_tasks.add_task(manager.broadcast_to_user, current_user.id, {"type": "DASHBOARD_UPDATED"})
