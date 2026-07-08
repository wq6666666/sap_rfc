from app.utils.sap_connect_pool import AsyncSapConnectionPool
from app.core.config import settings
from fastapi import HTTPException

asy_rfc_pool = AsyncSapConnectionPool(
    settings.conn_config,
    max_size=20, min_size=5
)

async def get_sap_connection():
    """依赖注入：从异步连接池获取连接"""
    conn = None
    try:
        conn = await asy_rfc_pool.get_connection()
        yield conn
    except TimeoutError as e:
        raise HTTPException(status_code=503, detail="SAP connection pool timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAP connection error: {str(e)}")
    finally:
        if conn:
            await asy_rfc_pool.return_connection(conn)


