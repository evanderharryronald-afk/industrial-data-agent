"""
EDA 工具的 HTTP 层。

仅负责 HTTP 请求处理、参数解析、调用 service.py 的业务逻辑、返回 HTTP 响应。
不含任何业务逻辑。
"""

from pathlib import Path

from fastapi import APIRouter

from tools.eda.schemas import EDARequest, EDAResponse
from tools.eda.service import run_eda

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
      "session_id": "conv-123",
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
      "columns": [
        {
          "name": "age",
          "dtype": "int64",
          "missing_count": 5,
          "missing_rate": 0.005,
          "unique_count": 50,
          "sample_values": [25, 30, 35]
        }
      ],
      "basic_stats": {
        "age": {
          "min": 18.0,
          "max": 80.0,
          "mean": 45.5,
          "std": 15.2,
          "median": 44.0
        }
      },
      "memory_usage_mb": 0.12,
      "target_column_info": {...},
      "warning_messages": ["⚠️ 列 'xxx' ..."],
      "metadata": {}
    }
    ```
    """
    workspace_root = get_workspace_root()
    return run_eda(
        dataset_path=request.dataset_path,
        workspace_root=workspace_root,
        target_column=request.target_column,
        detail_level=request.detail_level,
    )
