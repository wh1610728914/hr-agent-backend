# 数据库的依赖注入 (异步)
from backend.db.database import SessionLocal


async def get_db():
    async with SessionLocal() as session:
        try:
            yield session  # 把session 交给路由函数用
            # 没问题就提交
            await session.commit()
        except Exception:
            await session.rollback()  # 出问题回滚
            raise
        finally:
            await session.close()  # 最后 关闭
