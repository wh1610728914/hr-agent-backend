# 相关的模块性代码
import asyncio
import sys

from backend.db.database import SessionLocal
from backend.repository.auth import UserRepo


# 写初始化代码
async def init_user():
    async with SessionLocal() as session:
        async with session.begin():
            user_repo = UserRepo(session)
            user_dict_list = [
                {
                    "username": "Boss",
                    "password": "111111",
                    "email": "boss@qq.com",
                    "realname": "任老板",
                    "is_superuser": True,
                    # # "department_id": hr_department.id,
                },
                {
                    "username": "hr",
                    "password": "111111",
                    "email": "hr@qq.com",
                    "realname": "周HR",
                    "is_superuser": False,
                    # # "department_id": hr_department.id,
                },
                {
                    "username": "tech",
                    "password": "111111",
                    "email": "tech@qq.com",
                    "realname": "张技术",
                    "is_superuser": False,
                    # "department_id": tech_department.id,
                },
                {
                    "username": "operator",
                    "password": "111111",
                    "email": "operator@qq.com",
                    "realname": "孙运营",
                    "is_superuser": False,
                    # "department_id": operator_department.id,
                },
                {
                    "username": "market",
                    "password": "111111",
                    "email": "market@qq.com",
                    "realname": "李市场",
                    "is_superuser": False,
                    # "department_id": market_department.id,
                },
                {
                    "username": "finance",
                    "password": "111111",
                    "email": "finance@qq.com",
                    "realname": "王财务",
                    "is_superuser": False,
                    # "department_id": finance_department.id,
                },
                {
                    "username": "legal",
                    "password": "111111",
                    "email": "legal@qq.com",
                    "realname": "赵法务",
                    "is_superuser": False,
                    # "department_id": legal_department.id,
                },
                {
                    "username": "admin",
                    "password": "111111",
                    "email": "admin@qq.com",
                    "realname": "王行政",
                    "is_superuser": False,
                    # "department_id": admin_department.id,
                },
                {
                    "username": "service",
                    "password": "111111",
                    "email": "service@qq.com",
                    "realname": "张客服",
                    "is_superuser": False,
                    # "department_id": customer_service_department.id,
                },
            ]
            for user_dict in user_dict_list:
                await user_repo.create_user(user_dict)
        print("用户初始化完成")


async def main():

    await init_user()


if __name__ == "__main__":
    if sys.platform == "win32":
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(main())
    else:
        asyncio.run(main())
