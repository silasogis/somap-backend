from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_db, get_current_user
from app.models.workspace import Workspace
from app.models.user import User, UserRole
from app.schemas.workspace import WorkspaceResponse

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])

@router.get("", response_model=list[WorkspaceResponse])
async def get_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.admin:
        result = await db.execute(select(Workspace).order_by(Workspace.name))
    else:
        result = await db.execute(
            select(Workspace)
            .join(Workspace.users)
            .where(User.id == current_user.id)
            .order_by(Workspace.name)
        )
    workspaces = result.scalars().all()
    return workspaces

