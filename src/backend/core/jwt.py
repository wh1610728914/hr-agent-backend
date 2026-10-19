import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime
from enum import Enum
from backend.settings import settings

from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

# pyjwt: pip install pyjwt==2.10.1


from threading import Lock


class SingletonMeta(type):
    """
    单例:整个应用只创建一个实例，所有地方共用
    """

    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        """
        __call__：拦截类的实例化过程
        """

        with cls._lock:  # 如果是锁住状态的话
            if cls not in cls._instances:
                """没有这个实例，就去创建"""
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class TokenTypeEnum(Enum):
    ACCESS_TOKEN = 1
    REFRESH_TOKEN = 2


class AuthHandler(metaclass=SingletonMeta):
    security = HTTPBearer()
    # Authorization: Bearer {token}

    secret = settings.JWT_SECRET_KEY

    def _encode_token(self, iss: str, type: TokenTypeEnum):
        """核心编码方法：生成 JWT Token（内部使用）"""
        payload = dict(iss=str(iss), sub=str(type.value))
        to_encode = payload.copy()
        if type == TokenTypeEnum.ACCESS_TOKEN:
            exp = datetime.now() + settings.JWT_ACCESS_TOKEN_EXPIRES
        else:
            exp = datetime.now() + settings.JWT_REFRESH_TOKEN_EXPIRES
        to_encode.update({"exp": int(exp.timestamp())})
        return jwt.encode(to_encode, self.secret, algorithm="HS256")

    def encode_login_token(self, iss: str):
        """生成登录凭证：同时签发 Access Token 和 Refresh Token"""
        access_token = self._encode_token(iss, TokenTypeEnum.ACCESS_TOKEN)
        refresh_token = self._encode_token(iss, TokenTypeEnum.REFRESH_TOKEN)
        login_token = dict(
            access_token=f"{access_token}", refresh_token=f"{refresh_token}"
        )
        return login_token

    def encode_update_token(self, iss: str):
        """刷新凭证：仅签发新的 Access Token（通常配合 Refresh Token 使用）"""
        access_token = self._encode_token(iss, TokenTypeEnum.ACCESS_TOKEN)

        update_token = dict(access_token=f"{access_token}")
        return update_token

    def decode_access_token(self, token):
        """解码并校验 Access Token，返回签发者标识(iss)"""
        # ACCESS TOKEN：不可用（过期，或有问题），都用403错误
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            if payload["sub"] != str(TokenTypeEnum.ACCESS_TOKEN.value):
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Token类型错误！"
                )
            return payload["iss"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Access Token已过期！"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Access Token不可用！"
            )

    def decode_refresh_token(self, token):
        """解码并校验 Refresh Token，返回签发者标识(iss)"""
        # REFRESH TOKEN：不可用（过期，或有问题），都用401错误
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            if payload["sub"] != str(TokenTypeEnum.REFRESH_TOKEN.value):
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, detail="Token类型错误！"
                )
            return payload["iss"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Refresh Token已过期！"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Refresh Token不可用！"
            )

    def auth_access_dependency(
        self, auth: HTTPAuthorizationCredentials = Security(security)
    ):
        """FastAPI 依赖注入：从请求头提取并验证 Access Token"""
        return self.decode_access_token(auth.credentials)

    def auth_refresh_dependency(
        self, auth: HTTPAuthorizationCredentials = Security(security)
    ):
        """FastAPI 依赖注入：从请求头提取并验证 Refresh Token"""
        return self.decode_refresh_token(auth.credentials)
