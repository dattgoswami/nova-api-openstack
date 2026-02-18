"""
RealOpenStackClient — skeleton wiring openstacksdk to OpenStackClientBase.

This file is intentionally left as a skeleton. In a production deployment:
1. Install openstack SDK: pip install openstacksdk
2. Configure credentials via environment variables or clouds.yaml
3. Implement each method using openstack.compute.v2 resources

See: https://docs.openstack.org/openstacksdk/latest/user/guides/compute.html
"""

from app.infra.openstack.base import (
    FlavorRecord,
    ImageRecord,
    OpenStackClientBase,
    ServerRecord,
)


class RealOpenStackClient(OpenStackClientBase):
    """
    Production OpenStack client using openstacksdk.

    Instantiate via: RealOpenStackClient.from_settings()
    """

    def __init__(self) -> None:
        # In production, initialize the openstack connection here:
        #
        # import openstack
        # self._conn = openstack.connect(
        #     auth_url=settings.openstack_auth_url,
        #     project_name=settings.openstack_project_name,
        #     username=settings.openstack_username,
        #     password=settings.openstack_password,
        #     region_name=settings.openstack_region,
        # )
        raise NotImplementedError(
            "RealOpenStackClient is a skeleton. Install openstacksdk and implement the methods."
        )

    async def create_server(self, name: str, flavor_id: str, image_id: str) -> ServerRecord:
        # conn.compute.create_server(name=name, flavor_id=flavor_id, image_id=image_id)
        raise NotImplementedError

    async def get_server(self, server_id: str) -> ServerRecord | None:
        # conn.compute.get_server(server_id)
        raise NotImplementedError

    async def list_servers(self, limit: int, offset: int) -> tuple[list[ServerRecord], int]:
        # conn.compute.servers(limit=limit)
        raise NotImplementedError

    async def update_server(self, server_id: str, name: str) -> ServerRecord:
        # conn.compute.update_server(server_id, name=name)
        raise NotImplementedError

    async def delete_server(self, server_id: str) -> None:
        # conn.compute.delete_server(server_id)
        raise NotImplementedError

    async def perform_action(self, server_id: str, action: str, **kwargs: object) -> ServerRecord:
        # match action:
        #     case "start": conn.compute.start_server(server_id)
        #     case "stop": conn.compute.stop_server(server_id)
        #     case "reboot": conn.compute.reboot_server(server_id, "SOFT")
        #     case "resize": conn.compute.resize_server(server_id, kwargs["flavor_id"])
        raise NotImplementedError

    async def get_flavor(self, flavor_id: str) -> FlavorRecord | None:
        # conn.compute.get_flavor(flavor_id)
        raise NotImplementedError

    async def list_flavors(self, limit: int, offset: int) -> tuple[list[FlavorRecord], int]:
        # list(conn.compute.flavors())
        raise NotImplementedError

    async def get_image(self, image_id: str) -> ImageRecord | None:
        # conn.image.get_image(image_id)
        raise NotImplementedError

    async def list_images(self, limit: int, offset: int) -> tuple[list[ImageRecord], int]:
        # list(conn.image.images())
        raise NotImplementedError
