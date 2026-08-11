"""Data Import 工具的 HTTP 层。"""

import logging
from pathlib import Path

from fastapi import APIRouter

from tools.data_import.schemas import DataImportRequest, DataImportResponse
from tools.data_import.service import import_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tools/data_import", tags=["Data Import"])


def get_workspace_root() -> Path:
    """获取 workspace 根目录的绝对路径。"""
    project_root = Path(__file__).parent.parent.parent
    workspace = project_root / "workspace"
    return workspace


@router.post("/import", response_model=DataImportResponse)
def import_dataset(request: DataImportRequest) -> DataImportResponse:
    logger.info(
        f"Data import request - conversation_id: {request.conversation_id}, "
        f"file_name: {request.file_name}"
    )

    workspace_root = get_workspace_root()
    result = import_data(
        file_url=request.file_url,
        file_name=request.file_name,
        conversation_id=request.conversation_id,
        workspace_root=workspace_root,
    )

    logger.info(
        f"Data import completed - conversation_id: {request.conversation_id}, "
        f"status: {result.status}, dataset_path: {result.dataset_path}"
    )

    return result