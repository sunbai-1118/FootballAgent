"""统一响应格式：所有接口返回 {code, message, data} 结构"""
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

"""操作成功响应"""
def success(data: Any = None, message: str = "success", code: int = 200) -> dict:
    content =  {"code": code, "message": message, "data": data}
    # 目标： 把任何FastAPI，pydantic, ORM对象都正常响应为code，message,data
    return JSONResponse(content= jsonable_encoder(content))


# """操作失败响应"""
# def error(code: int = 400, message: str = "error", data: Any = None) -> dict:
#     content = {"code": code, "message": message, "data": data}
#     # 目标： 把任何FastAPI，pydantic, ORM对象都正常响应为code，message,data
#     return JSONResponse(content= jsonable_encoder(content))


