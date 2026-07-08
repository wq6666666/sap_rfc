import asyncio
from asyncio import Queue
from pyrfc import Connection
import logging

logger = logging.getLogger(__name__)

_CONN_CREATE_TIMEOUT = 10
_CONN_PING_TIMEOUT = 5
_POOL_GET_TIMEOUT = 30
_HEALTH_CHECK_INTERVAL = 30
_HEALTH_CHECK_SAMPLE = 3


class AsyncSapConnectionPool:
    """
    异步 SAP 连接池

    维护一个 pyrfc.Connection 缓存池，支持并发获取/归还、
    定期健康检查，以及优雅关闭。
    """

    def __init__(
            self,
            config: dict,
            max_size: int = 10,
            min_size: int = 2,
    ):
        self.config = config
        self.max_size = max_size
        self.min_size = min_size

        self._pool: Queue = Queue(maxsize=max_size)
        self._lock = asyncio.Lock()
        self._is_closed = False
        self._health_check_task: asyncio.Task | None = None

    # ---------------------------------------------------------------
    #  内部辅助方法
    # ---------------------------------------------------------------

    async def _create_connection(self) -> Connection:
        """在 executor 中创建同步 pyrfc.Connection（带超时）。"""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._sync_create_connection),
                timeout=_CONN_CREATE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise TimeoutError("SAP connection creation timed out")

    def _sync_create_connection(self) -> Connection:
        return Connection(**self.config)

    async def _is_connection_alive(self, conn: Connection) -> bool:
        """通过 RFC_PING 检查连接是否存活。"""
        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, conn.call, 'RFC_PING'),
                timeout=_CONN_PING_TIMEOUT,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def _safe_close(conn: Connection):
        try:
            conn.close()
        except Exception:
            pass

    # ---------------------------------------------------------------
    #  初始化 / 生命周期
    # ---------------------------------------------------------------

    async def initialize(self):
        """创建 min_size 个初始连接，并启动健康检查后台任务。"""
        for _ in range(self.min_size):
            try:
                conn = await self._create_connection()
                await self._pool.put(conn)
            except Exception as e:
                logger.warning("Init connection failed: %s", e)

        # 初始化后立即补充到 min_size
        await self._ensure_min_pool()

        self._health_check_task = asyncio.create_task(
            self._health_check_loop(),
            name="sap-pool-health-check",
        )

    # ---------------------------------------------------------------
    #  健康检查
    # ---------------------------------------------------------------

    async def _health_check_loop(self):
        """定时抽样检查连接存活，失效即关闭并补充。"""
        while not self._is_closed:
            try:
                await asyncio.sleep(_HEALTH_CHECK_INTERVAL)

                # 逐个串行检查，每次取一个 -> ping -> 立即放回
                # 避免批量取出导致池容量临时缩水
                max_check = min(_HEALTH_CHECK_SAMPLE, self._pool.qsize())
                for _ in range(max_check):
                    try:
                        conn = self._pool.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                    if await self._is_connection_alive(conn):
                        await self._pool.put(conn)
                    else:
                        self._safe_close(conn)

                await self._ensure_min_pool()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Health check error (recovering)")

    async def _ensure_min_pool(self):
        """保底补充连接至 min_size 水位。"""
        async with self._lock:
            while self._pool.qsize() < self.min_size:
                if self._pool.qsize() >= self.max_size:
                    break
                try:
                    conn = await self._create_connection()
                    await self._pool.put(conn)
                except Exception:
                    break

    # ---------------------------------------------------------------
    #  对外接口
    # ---------------------------------------------------------------

    async def get_connection(self) -> Connection:
        """
        获取一个可用连接。

        流程：快速路径（池中有空闲）→ ping 验证 → 返回
              慢速路径（池空 / 连接失效）→ 加锁创建新连接，不超 max_size
        """
        if self._is_closed:
            raise RuntimeError("Pool is closed")

        # --- 快速路径：从池中直接拿一个 ----------------------------------
        try:
            conn = self._pool.get_nowait()
        except asyncio.QueueEmpty:
            conn = None

        if conn is not None:
            if await self._is_connection_alive(conn):
                return conn
            # 连接已失效，丢弃
            self._safe_close(conn)

        # --- 慢速路径：在锁的保护下创建 / 等待 ----------------------------
        async with self._lock:
            # 双重检查：等锁期间也许有连接被归还
            try:
                conn = self._pool.get_nowait()
            except asyncio.QueueEmpty:
                conn = None

            if conn is not None:
                if await self._is_connection_alive(conn):
                    return conn
                self._safe_close(conn)

            # 池子还有空位 -> 新建
            if self._pool.qsize() < self.max_size:
                conn = await self._create_connection()
                return conn

            # 池子满了 -> 阻塞等待归还
            try:
                conn = await asyncio.wait_for(
                    self._pool.get(),
                    timeout=_POOL_GET_TIMEOUT,
                )
            except asyncio.TimeoutError:
                raise TimeoutError("SAP connection pool timeout (all connections busy)")

            return conn

    async def return_connection(self, conn: Connection):
        """将连接归还池中；池已关闭则直接断开。"""
        if self._is_closed:
            self._safe_close(conn)
            return

        try:
            await self._pool.put(conn)
        except Exception:
            self._safe_close(conn)

    # ---------------------------------------------------------------
    #  关闭
    # ---------------------------------------------------------------

    async def close(self):
        """关闭池：取消健康检查、清空并断开所有连接。"""
        self._is_closed = True

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                self._safe_close(conn)
            except Exception:
                pass




