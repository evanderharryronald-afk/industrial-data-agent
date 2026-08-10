"""
FastAPI 主应用。

挂载所有工具的 router，目前是单进程部署（方便前期开发和调试）。
未来若某个工具需要独立部署，只需把它的 router 注释掉、搬出去起独立服务，
其他工具代码完全不受影响。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tools.eda.router import router as eda_router

# 创建 FastAPI 应用
app = FastAPI(
    title="Industrial Data Agent - Tools Service",
    description="提供确定性数据处理工具的 HTTP API。",
    version="0.1.0",
    servers=[
        {
            "url": "http://host.docker.internal:8000",
            "description": "Local development server (accessible from Docker)"
        },
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
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
