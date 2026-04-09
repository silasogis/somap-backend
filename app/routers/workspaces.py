from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_db, get_current_user
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceResponse

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])

@router.get("", response_model=list[WorkspaceResponse])
async def get_workspaces(
    db: AsyncSession = Depends(get_db),
    _ = Depends(get_current_user)
):
    result = await db.execute(select(Workspace).order_by(Workspace.name))
    workspaces = result.scalars().all()
    return workspaces
