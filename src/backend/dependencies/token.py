from backend.core.token import AuthHandler


def get_auth_handler():
    """token的依赖注入"""
    return AuthHandler()
