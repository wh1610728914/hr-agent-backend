from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from backend.utils.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    valid_exception_handler,
    excep_exception_handler,
)
from backend.settings import settings
from backend.apis import api

app = FastAPI()
app.include_router(api)
# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, valid_exception_handler)
app.add_exception_handler(Exception, excep_exception_handler)
# origins = ['']
