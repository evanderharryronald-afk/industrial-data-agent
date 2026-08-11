"""
EDA 工具的 HTTP 层。

仅负责 HTTP 请求处理、参数解析、调用 service.py 的业务逻辑、返回 HTTP 响应。
不含任何业务逻辑。
"""

import logging
from pathlib import Path

from fastapi import APIRouter

from tools.eda.schemas import EDARequest, EDAResponse
from tools.eda.service import run_eda

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tools/eda", tags=["EDA"])


def get_workspace_root() -> Path:
    """获取 workspace 根目录的绝对路径。"""
    # 相对于项目根目录
    project_root = Path(__file__).parent.parent.parent  # tools/eda/router.py -> 项目根
    workspace = project_root / "workspace"
    return workspace


@router.post("/analyze", response_model=EDAResponse)
def analyze_dataset(request: EDARequest) -> EDAResponse:
    """
    执行数据集 EDA 分析。

    接收一个数据集路径和可选的目标列名，返回数据集的元特征、统计信息和质量警告。

    **输入示例**：
    ```json
    {
      "conversation_id": "conv-123",
      "dataset_path": "raw_data.csv",
      "target_column": "sales",
      "detail_level": "basic"
    }
    ```

    **返回示例**：
    ```json
    {
      "status": "success",
      "error_message": null,
      "dataset_shape": [1000, 15],
      "columns": [...],
      "basic_stats": {...},
      "memory_usage_mb": 0.12,
      "target_column_info": {...},
      "warning_messages": [...],
      "metadata": {}
    }
    ```
    """
    logger.info(
        f"EDA request received - conversation_id: {request.conversation_id}, dataset_path: {request.dataset_path}"
    )
    
    workspace_root = get_workspace_root()
    result = run_eda(
        dataset_path=request.dataset_path,
        workspace_root=workspace_root,
        target_column=request.target_column,
        detail_level=request.detail_level,
        conversation_id=request.conversation_id,
    )
    
    logger.info(
        f"EDA completed - conversation_id: {request.conversation_id}, status: {result.status}"
    )
    return result
