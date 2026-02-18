from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: str
    name: str
    os_distro: str
    min_disk_gb: int
    size_bytes: int
    status: str

    model_config = {"from_attributes": True}
