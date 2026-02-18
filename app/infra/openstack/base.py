from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.server import ServerStatus


@dataclass
class ServerRecord:
    id: str
    name: str
    status: ServerStatus
    flavor_id: str
    image_id: str
    ip_address: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class FlavorRecord:
    id: str
    name: str
    vcpus: int
    ram_mb: int
    disk_gb: int


@dataclass
class ImageRecord:
    id: str
    name: str
    os_distro: str
    min_disk_gb: int
    size_bytes: int
    status: str


class OpenStackClientBase(ABC):
    """Abstract base class mirroring the openstacksdk interface for server lifecycle management."""

    # --- Server operations ---

    @abstractmethod
    async def create_server(
        self,
        name: str,
        flavor_id: str,
        image_id: str,
    ) -> ServerRecord: ...

    @abstractmethod
    async def get_server(self, server_id: str) -> ServerRecord | None: ...

    @abstractmethod
    async def list_servers(self, limit: int, offset: int) -> tuple[list[ServerRecord], int]: ...

    @abstractmethod
    async def update_server(self, server_id: str, name: str) -> ServerRecord: ...

    @abstractmethod
    async def delete_server(self, server_id: str) -> None: ...

    @abstractmethod
    async def perform_action(
        self,
        server_id: str,
        action: str,
        **kwargs: object,
    ) -> ServerRecord: ...

    # --- Flavor operations ---

    @abstractmethod
    async def get_flavor(self, flavor_id: str) -> FlavorRecord | None: ...

    @abstractmethod
    async def list_flavors(self, limit: int, offset: int) -> tuple[list[FlavorRecord], int]: ...

    # --- Image operations ---

    @abstractmethod
    async def get_image(self, image_id: str) -> ImageRecord | None: ...

    @abstractmethod
    async def list_images(self, limit: int, offset: int) -> tuple[list[ImageRecord], int]: ...
