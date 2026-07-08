from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from app.core.rfc_config import asy_rfc_pool, get_sap_connection
from pyrfc import Connection, RFCError
from app.utils.response import success_response
from .shemas import DynamicRFCRequest



@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化连接池，关闭时清理。"""
    await asy_rfc_pool.initialize()
    yield
    await asy_rfc_pool.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.post("/call-dynamic-rfc")
async def call_dynamic_rfc(
        request: DynamicRFCRequest,
        connection: Connection = Depends(get_sap_connection)
):
    with connection as conn:
        try:
            all_params = {**request.import_params, **request.changing_params, **request.table_params}
            result = conn.call(request.rfc_name, **all_params)
            return success_response("调用成功",result)
        except RFCError as e:
            print(f"RFC execution failed: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except TimeoutError as e:
            print(f"Connection timeout: {e}")
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

