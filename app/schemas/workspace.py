from pydantic import BaseModel, ConfigDict
from humps import camelize

class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=camelize,
        populate_by_name=True,
        from_attributes=True,
    )
    id: str
    name: str
    slug: str
    description: str
