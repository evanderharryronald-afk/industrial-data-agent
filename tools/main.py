"""
FastAPI 主应用。

挂载所有工具的 router，目前是单进程部署（方便前期开发和调试）。
未来若某个工具需要独立部署，只需把它的 router 注释掉、搬出去起独立服务，
其他工具代码完全不受影响。
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from tools.eda.router import router as eda_router
from tools.data_import.router import router as data_import_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Industrial Data Agent - Tools Service",
    description="提供确定性数据处理工具的 HTTP API。",
    version="0.1.0",
    servers=[
        {
            "url": "http://host.docker.internal:8000",
            "description": "Docker 容器可访问的宿主机地址"
        },
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        },
        {
            "url": "http://192.168.1.30:8000",
            "description": "Local IP server"
        }
    ]
)

# CORS 配置（开发阶段允许所有源，生产环境应该限制）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载各工具的 router
app.include_router(eda_router)
app.include_router(data_import_router)

# 挂载静态文件服务（用于返回 workspace 下的图片等资源）
workspace_path = Path(__file__).parent.parent / "workspace"
workspace_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(workspace_path)), name="static")

logger.info(f"Static files mounted at /static, serving from: {workspace_path}")

# 简单的健康检查端点
@app.get("/health")
def health_check():
    """健康检查端点。"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # 本地开发用 uvicorn 起服务
    # 生产环境可用 gunicorn/hypercorn 等
    uvicorn.run(
        "tools.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
