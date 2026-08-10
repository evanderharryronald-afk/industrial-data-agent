"""
EDA 工具的 Pydantic schema。

定义了 EDA 工具的请求和响应格式。LLM 通过这里的 description 字段
理解参数含义和返回值结构，因此每个字段的 description 都要写得清楚。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from shared.base_schemas import ToolRequestBase, ToolResponseBase


class EDARequest(ToolRequestBase):
    """EDA 工具的请求模型。"""

    dataset_path: str = Field(
        description=(
            "数据集文件的相对路径（基于 workspace/{session_id}/ 目录），"
            "支持格式：.csv、.parquet。"
            "通常来自数据导入工具、或前一步清洗/处理工具的返回值。"
        )
    )
    detail_level: Literal["basic", "detailed"] = Field(
        default="basic",
        description=(
            "EDA 详细程度。"
            "'basic'：快速返回列名、类型、缺失率、基本统计量（秒级）；"
            "'detailed'：生成完整分析报告（可能耗时较长，预留给未来高级功能）。"
            "当前阶段推荐使用 'basic'。"
        ),
    )
    target_column: str | None = Field(
        default=None,
        description=(
            "目标列名（可选）。若指定，EDA 会额外输出该列的统计信息。"
            "用于分类/回归任务时，帮助 LLM 判断目标列是否合理。"
        ),
    )


class ColumnInfo(BaseModel):
    """单个列的元信息。"""

    name: str = Field(description="列名")
    dtype: str = Field(description="数据类型（如 int64, float64, object）")
    missing_count: int = Field(description="缺失值个数")
    missing_rate: float = Field(description="缺失率（0-1 之间）")
    unique_count: int = Field(description="唯一值个数")
    sample_values: list[Any] = Field(
        description="前 3 个非空样例值，帮助 LLM 判断数据内容是否符合预期"
    )


class BasicStats(BaseModel):
    """基本统计信息。"""

    min: float | None = Field(default=None, description="最小值（仅数值列）")
    max: float | None = Field(default=None, description="最大值（仅数值列）")
    mean: float | None = Field(default=None, description="平均值（仅数值列）")
    std: float | None = Field(default=None, description="标准差（仅数值列）")
    median: float | None = Field(default=None, description="中位数（仅数值列）")


class EDAResponse(ToolResponseBase):
    """EDA 工具的响应模型。"""

    dataset_shape: tuple[int, int] = Field(
        description="数据集形状 (行数, 列数)"
    )
    columns: list[ColumnInfo] = Field(
        description="所有列的元信息列表"
    )
    basic_stats: dict[str, BasicStats] = Field(
        description=(
            "各数值列的基本统计（min, max, mean, std, median）。"
            "非数值列的 key 会被跳过。LLM 可从这里快速了解数据分布。"
        )
    )
    memory_usage_mb: float = Field(
        description="数据集内存占用（MB）"
    )
    target_column_info: ColumnInfo | None = Field(
        default=None,
        description=(
            "目标列的详细信息（仅在 request 中指定了 target_column 时才有值）。"
            "帮助 LLM 判断目标列的分布是否适合建模。"
        ),
    )
    warning_messages: list[str] = Field(
        default_factory=list,
        description=(
            "数据质量警告（如某列 100% 缺失、某列只有 1 个唯一值等）。"
            "LLM 应该根据这些警告调整后续处理策略。"
        ),
    )
