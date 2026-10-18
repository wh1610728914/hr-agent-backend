# 这个是操作数据库
from sqlalchemy.ext.asyncio import AsyncSession

# 给所有数据库操作的类 立规矩


class BaseRepo:
    def __init__(self, session: AsyncSession):
        # 这样对象就可以随时用self.session 访问数据库了
        self.session = session
