# 下载 uv add passlib
from passlib.context import CryptContext

# passlib 是专门用来处理密码哈希的python库，作用是：把明文密码变成一串不可逆的乱码，并提供校验功能

# 初始化密码哈希上下文
pwd_context = CryptContext(
    # 告诉passlib用bcrypt算法来加密密码，这里可以配置多种算法！可以做成 兼容新旧密码
    # 且用户登录成功后，自动升级为新算法
    # 索引靠前的算法 叫 新算法
    schemes=["bcrypt"],
    # 自动启用旧算法
    deprecated="auto",
)


def hash_password(password: str):
    """把明文密码加密成哈希值"""
    return pwd_context.hash(password)


def verify_password(plain_pwd: str, hash_pwd: str):
    """校验明文密码和哈希值是否匹配"""
    return pwd_context.verify(plain_pwd, hash_pwd)
