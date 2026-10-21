from backend.core.exceptions import BusinessException
from backend.models.department import DepartmentModel
from backend.models.ding import DingDingModel
from backend.models.user import UserModel
from backend.repository import BaseRepo
from backend.schemas.hr import AssignDepartmentRequest
from backend.schemas.user import DingUserResponse
from sqlalchemy.orm import selectinload
from sqlalchemy import func, select


class UserRepo(BaseRepo):
    """"""

    async def create_user(self, info):
        """创建用户"""
        user = UserModel(**info)
        self.session.add(user)
        await self.session.flush()  # 发SQL,但不关闭事务
        await self.session.refresh(user)  # 此时事务还开着，refresh不会报错
        return user

    async def check_by_id(self, id: str):
        """通过id校验"""
        user = await self.session.scalar(select(UserModel).where(UserModel.id == id))
        return user

    async def check_by_email(self, email: str):
        """邮箱登录"""
        user = await self.session.scalar(
            select(UserModel).where(UserModel.email == email)
        )
        return user

    async def get_by_time(self, time_str: str):
        """获取根据创建日期获取"""
        res = await self.session.execute(
            select(UserModel).where(UserModel.create_at >= time_str)
        )
        users = res.scalars().all()
        return users

    async def get_user_list(self, page: int, size: int, department_id: str | None):
        """获取用户列表"""
        # 1.基础查询
        stmt = select(UserModel)
        if department_id:
            stmt = stmt.where(UserModel.department_id == department_id)

        # 2.计算总数
        # with_only_columns 只保留这些列（sqlalchemy会拿到现有的stmt，去查询）-- 快捷方便
        stmt_total = stmt.with_only_columns(
            func.count(UserModel.id)
            # order_by(None)在执行这个总数查询时，把所有的排序规则都给我清除掉，让它只专注于快速数数。
        ).order_by(None)
        total = await self.session.scalar(stmt_total)

        # 3，分页越界拦截（性能保护）
        offset = (page - 1) * size
        if offset >= total:
            return total, []

        # 4.查当前页数据
        stmt = stmt.limit(size).offset(offset).order_by(UserModel.create_at.desc())

        users = await self.session.scalars(stmt)

        return total, users.all()

    async def set_dingding_user(self, user_id: str, dingding_user_data: dict):
        """设置钉钉获得的user信息"""

        user = self.check_by_id(user_id)
        if not user:
            raise BusinessException(message="设置钉钉的用户不存在")
        dingding_user = await self.session.scalar(
            select(DingDingModel).where(DingDingModel.user_id == user_id)
        )
        if dingding_user:
            for key, value in dingding_user_data.items():
                # 等价于 obj.key = value
                setattr(dingding_user, key, value)
        else:
            dingding_user = DingDingModel(**dingding_user_data, user_id=user_id)
            self.session.add(dingding_user)
        return dingding_user

    async def get_ding_info(self, user_id: str) -> DingUserResponse | None:
        """获取钉钉用户信息"""
        info = await self.session.scalar(
            select(DingDingModel).where(user_id == DingDingModel.user_id)
        )
        if not info:
            raise BusinessException(message="无该用户信息")
        return info

    async def get_by_hr(self, page: int, size: int):
        """获取hr的总列表"""
        stmt = select(UserModel).where(UserModel.is_hr == True)
        stmt_total = select(func.count(UserModel.id))
        total = await self.session.scalar(stmt_total)
        limit = size
        offset = (page - 1) * size
        stmt = stmt.limit(limit).offset(offset).order_by(UserModel.create_at.desc())
        hr_list = (await self.session.scalars(stmt)).all()

        return total, hr_list

    async def assign_departs(self, data: AssignDepartmentRequest):
        """给hr分配部门"""
        hr_stmt = (
            select(UserModel).where(UserModel.id == data.hr_id)
            # options 告诉数据库，再帮我多拿点数据过来
            .options(
                # selectinload 用来预加载的，sqlalchemy默认的懒加载，
                # 不加这个的话，是不会去查询managed_departments的，那么最后的赋值就会报错
                selectinload(UserModel.managed_departments)
            )
        )
        hr: UserModel = await self.session.scalar(hr_stmt)
        if not hr:
            raise BusinessException(message="该用户不存在")
        department_stmt = select(DepartmentModel).where(
            DepartmentModel.id.in_(data.department_ids)
        )
        departments = (await self.session.scalars(department_stmt)).all()
        hr.managed_departments = departments
        return departments
