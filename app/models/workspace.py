from sqlalchemy import String, Text, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from uuid import uuid4

user_workspace_association = Table(
    "user_workspaces",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
)

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")

    layers: Mapped[list["Layer"]] = relationship(back_populates="workspace")
    users: Mapped[list["User"]] = relationship(secondary="user_workspaces", back_populates="workspaces")

