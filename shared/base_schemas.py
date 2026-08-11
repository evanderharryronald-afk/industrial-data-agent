"""
公共 BaseSchema。

几乎所有工具的 request 都需要 conversation_id 来定位 workspace/{conversation_id}/ 下的文件，
response 都需要 status/error_message 来表达成功/失败。抽成基类，
各工具在 schemas.py 里继承，避免重复定义，也方便以后统一加字段（如 workspace_id）。

注意：这里只放"跨工具通用"的字段。工具专属的输入输出字段（如 dataset_path、
target_column）不要塞进这里，留给各工具自己的 schemas.py 定义。
"""

from typing import Literal

from pydantic import BaseModel, Field


class ToolRequestBase(BaseModel):
    """所有工具 Request 的公共基类。"""

    conversation_id: str = Field(
        description=(
            "Dify 对话的唯一标识，用于定位 workspace/{conversation_id}/ 下的文件。"
            "直接从 Dify 的上下文自动填充。"
        )
    )


class ToolResponseBase(BaseModel):
    """所有工具 Response 的公共基类。"""

    status: Literal["success", "error"] = Field(
        description="本次工具调用是否成功。LLM 应先检查这个字段，"
        "为 error 时应结合 error_message 向用户说明原因，而不是继续解析其他字段。"
    )
    error_message: str | None = Field(
        default=None,
        description="status 为 error 时的错误说明，用于 LLM 向用户解释失败原因。"
        "status 为 success 时该字段为 null。",
    )
    metadata: dict = Field(
        default_factory=dict,
        description=(
            "预留字段，装暂不确定是否需要固化为正式字段的辅助信息（如耗时、内部调试信息）。"
            "工具的核心结果必须放在各自 Response 的正式字段里，不要依赖 LLM 从 metadata 里"
            "解析关键结果——metadata 只是锦上添花的附加信息。"
        ),
    )
