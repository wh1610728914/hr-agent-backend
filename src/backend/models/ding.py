from backend.db.database import BaseTable
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class DingDingModel(BaseTable):
    """钉钉"""

    __tablename__ = "dings"

    nick: Mapped[str] = mapped_column(String(100), nullable=False, comment="昵称")
    union_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="用户在同一个开发者企业主体下的唯一ID",
    )
    open_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="用户某个特定应用下的唯一ID",
    )
    mobile: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False, comment="手机号"
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship(back_populates="dingding_user")
