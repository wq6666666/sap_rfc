from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

def success_response( message="success",data=None):
    #要把任何的FastAPI，Pydantic，Orm 对象都要正常响应 -> code message data
    content = {
        "code": 200,
        "message": message,
        "data": data
    }
    return JSONResponse(content=jsonable_encoder(content))