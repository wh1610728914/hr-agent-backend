from backend.utils.jwt import AuthHandler


async def get_auth_handler():
    """token的依赖注入"""
    return AuthHandler()
