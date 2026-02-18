from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.server import ServerStatus
from app.schemas.flavor import FlavorResponse
from app.schemas.image import ImageResponse


class ServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    flavor_id: str = Field(..., description="UUID of the flavor to use")
    image_id: str = Field(..., description="UUID of the image to boot from")


class ServerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class ServerResponse(BaseModel):
    id: str
    name: str
    status: ServerStatus
    flavor_id: str
    image_id: str
    ip_address: str | None
    created_at: datetime
    updated_at: datetime
    flavor: FlavorResponse | None = None
    image: ImageResponse | None = None

    model_config = {"from_attributes": True}


ActionType = Literal["start", "stop", "reboot", "resize"]


class ServerAction(BaseModel):
    action: ActionType
    flavor_id: str | None = Field(None, description="Required for resize action")

    @model_validator(mode="after")
    def validate_resize_requires_flavor(self) -> "ServerAction":
        if self.action == "resize" and not self.flavor_id:
            raise ValueError("flavor_id is required for resize action")
        if self.action != "resize" and self.flavor_id is not None:
            raise ValueError("flavor_id is only allowed for resize action")
        return self
