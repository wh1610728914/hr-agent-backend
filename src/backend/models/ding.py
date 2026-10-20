from backend.db.database import BaseTable
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class DingDingModel(BaseTable):
    """钉钉"""

    __tablename__ = "dings"

    nick: Mapped[str] = mapped_column(String(100), nullable=False, comment="")
    union_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    open_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    mobile: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship(back_populates="dingding_user")
