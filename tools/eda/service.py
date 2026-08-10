"""
EDA 业务逻辑层。

这层是完全独立的纯 Python 函数，不依赖 FastAPI，方便单元测试和后续复用。
"""

from pathlib import Path

import numpy as np
import pandas as pd

from tools.eda.schemas import BasicStats, ColumnInfo, EDAResponse


def load_dataset(file_path: str) -> pd.DataFrame:
    """加载数据集（支持 CSV 和 Parquet）。"""
    if file_path.endswith(".parquet"):
        return pd.read_parquet(file_path)
    elif file_path.endswith(".csv"):
        return pd.read_csv(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}. Use .csv or .parquet")


def get_column_info(series: pd.Series) -> ColumnInfo:
    """提取单个列的元信息。"""
    missing_count = series.isna().sum()
    missing_rate = missing_count / len(series) if len(series) > 0 else 0.0
    unique_count = series.nunique()

    # 获取 3 个样例值
    sample_values = series.dropna().head(3).tolist()

    return ColumnInfo(
        name=series.name,
        dtype=str(series.dtype),
        missing_count=int(missing_count),
        missing_rate=float(missing_rate),
        unique_count=int(unique_count),
        sample_values=sample_values,
    )


def get_basic_stats(series: pd.Series) -> BasicStats | None:
    """计算数值列的基本统计信息。"""
    if not pd.api.types.is_numeric_dtype(series):
        return None

    # 过滤掉缺失值
    valid_series = series.dropna()
    if len(valid_series) == 0:
        return None

    return BasicStats(
        min=float(valid_series.min()),
        max=float(valid_series.max()),
        mean=float(valid_series.mean()),
        std=float(valid_series.std()),
        median=float(valid_series.median()),
    )


def check_data_quality(df: pd.DataFrame, target_column: str | None = None) -> list[str]:
    """检查数据质量，返回警告信息列表。"""
    warnings = []

    # 全空列检查
    for col in df.columns:
        if df[col].isna().sum() == len(df):
            warnings.append(f"⚠️ 列 '{col}' 100% 缺失，建议删除或重新审视数据来源。")

    # 单值列检查
    for col in df.columns:
        if df[col].nunique() <= 1:
            warnings.append(f"⚠️ 列 '{col}' 只有 ≤1 个唯一值，可能无法用于特征。")

    # 目标列特殊检查
    if target_column and target_column in df.columns:
        target_missing_rate = df[target_column].isna().sum() / len(df)
        if target_missing_rate > 0.5:
            warnings.append(
                f"⚠️ 目标列 '{target_column}' 缺失率 > 50%，"
                f"可能无法进行有效建模。"
            )

    return warnings


def run_eda(
    dataset_path: str,
    workspace_root: str | Path = "workspace",
    target_column: str | None = None,
    detail_level: str = "basic",
) -> EDAResponse:
    """
    运行 EDA 分析。

    Args:
        dataset_path: 数据集相对路径（基于 workspace/{session_id}/）
        workspace_root: workspace 根目录路径
        target_column: 可选的目标列名
        detail_level: "basic" 或 "detailed"

    Returns:
        EDAResponse 对象
    """
    try:
        # 构造完整文件路径
        full_path = Path(workspace_root) / dataset_path
        if not full_path.exists():
            return EDAResponse(
                status="error",
                error_message=f"文件不存在：{full_path}",
                dataset_shape=(0, 0),
                columns=[],
                basic_stats={},
                memory_usage_mb=0.0,
            )

        # 加载数据集
        df = load_dataset(str(full_path))

        # 提取列信息
        columns_info = [get_column_info(df[col]) for col in df.columns]

        # 计算基本统计
        basic_stats = {}
        for col in df.columns:
            stats = get_basic_stats(df[col])
            if stats:
                basic_stats[col] = stats

        # 计算内存占用
        memory_usage_mb = float(df.memory_usage(deep=True).sum() / 1024**2)

        # 提取目标列信息
        target_column_info = None
        if target_column and target_column in df.columns:
            target_column_info = get_column_info(df[target_column])

        # 数据质量检查
        warnings = check_data_quality(df, target_column)

        return EDAResponse(
            status="success",
            dataset_shape=(len(df), len(df.columns)),
            columns=columns_info,
            basic_stats=basic_stats,
            memory_usage_mb=memory_usage_mb,
            target_column_info=target_column_info,
            warning_messages=warnings,
        )

    except Exception as e:
        return EDAResponse(
            status="error",
            error_message=f"EDA 执行失败：{str(e)}",
            dataset_shape=(0, 0),
            columns=[],
            basic_stats={},
            memory_usage_mb=0.0,
        )
