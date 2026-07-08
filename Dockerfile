FROM python:3.11.15

LABEL authors="xuwenqing" maintainer="xwq<wenqing814@outlook.com>"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1

ENV UV_LINK_MODE=copy

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

ADD nwrfc750P_18-80009783.tar.gz /usr/local/sap/

ENV SAPNWRFC_HOME="/usr/local/sap/nwrfc750P_18-80009783/nwrfcsdk"

ENV LD_LIBRARY_PATH=$SAPNWRFC_HOME/lib:$LD_LIBRARY_PATH

RUN test -f "$SAPNWRFC_HOME/lib/libsapnwrfc.so" &&  \
            echo "✅ SAP SDK found" || (echo "❌ SDK not found" && exit 1)

#缓存挂载,多次构建时,uv 的下载缓存会被复用,加速构建,临时挂载，只在 RUN 命令执行期间存在
# 将宿主机/构建上下文中的 uv.lock 文件挂载到容器内
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

COPY ./app /app/app

EXPOSE 8083

CMD ["uv","run","uvicorn","app.main:app","--port", "8083"]