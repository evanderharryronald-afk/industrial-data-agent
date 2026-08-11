"""Data Import 工具的 Pydantic schema."""

from pydantic import Field

from shared.base_schemas import ToolRequestBase, ToolResponseBase


class DataImportRequest(ToolRequestBase):
    """数据导入工具的请求模型。"""

    file_url: str = Field(
        description=(
            "Dify 文件预览/下载地址（相对路径，含签名参数，如 "
            "/files/xxx/file-preview?timestamp=...&nonce=...&sign=...）。"
            "来自 Dify File Upload 组件输出对象的 url 字段。"
            "该链接为一次性短时效签名直链，必须在获取后立即调用本工具下载，不能延迟使用。"
        )
    )
    file_name: str = Field(
        description=(
            "原始文件名（含扩展名），如 sales_data.xlsx。"
            "来自 Dify File Upload 组件输出对象的 filename 字段，用于判断文件格式。"
        )
    )


class DataImportResponse(ToolResponseBase):
    """数据导入工具的响应模型。"""

    dataset_path: str = Field(
        description=(
            "导入成功后的相对路径（基于 workspace/{conversation_id}/）。"
            "格式：raw/{filename}.parquet。后续工具可直接使用此路径。"
        )
    )
    rows: int = Field(description="导入的数据行数")
    columns: int = Field(description="导入的数据列数")
    column_names: list[str] = Field(description="所有列名列表")
    preview_data: list[dict] = Field(description="前 5 行数据预览（字典格式）")
    file_size_mb: float = Field(description="原始文件大小（MB）")