from pydantic import BaseModel


class FlavorResponse(BaseModel):
    id: str
    name: str
    vcpus: int
    ram_mb: int
    disk_gb: int

    model_config = {"from_attributes": True}
