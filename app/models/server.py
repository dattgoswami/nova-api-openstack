import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ServerStatus(str, enum.Enum):
    BUILD = "BUILD"
    ACTIVE = "ACTIVE"
    SHUTOFF = "SHUTOFF"
    REBOOT = "REBOOT"
    RESIZE = "RESIZE"
    VERIFY_RESIZE = "VERIFY_RESIZE"
    ERROR = "ERROR"
    DELETED = "DELETED"


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ServerStatus] = mapped_column(
        Enum(ServerStatus), nullable=False, default=ServerStatus.BUILD
    )
    flavor_id: Mapped[str] = mapped_column(String(36), ForeignKey("flavors.id"), nullable=False)
    image_id: Mapped[str] = mapped_column(String(36), ForeignKey("images.id"), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    flavor: Mapped["Flavor"] = relationship("Flavor", lazy="joined")  # type: ignore[name-defined]  # noqa: F821
    image: Mapped["Image"] = relationship("Image", lazy="joined")  # type: ignore[name-defined]  # noqa: F821
