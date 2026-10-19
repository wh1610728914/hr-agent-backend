from backend.core.jwt import AuthHandler


def get_auth_handler():
    """token的依赖注入"""
    return AuthHandler()
