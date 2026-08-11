"""Data Import 业务逻辑层。"""

import os
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

from tools.data_import.schemas import DataImportResponse


def get_dify_base_url() -> str:
    """获取 Dify 对外暴露的 base url（走 nginx 反代的那个地址）。

    这是拼接文件下载完整 URL 用的，不是鉴权凭证。
    本地部署默认是 http://localhost，如果 Dify 挂在其他端口/域名，
    通过环境变量 DIFY_BASE_URL 覆盖。
    """
    return os.getenv("DIFY_BASE_URL", "http://localhost")


def build_full_file_url(relative_url: str) -> str:
    """把 Dify 返回的相对路径拼接成完整可访问 URL。

    Args:
        relative_url: Dify 传入的相对路径，如 /files/xxx/file-preview?...

    Returns:
        完整 URL
    """
    if relative_url.startswith("http"):
        return relative_url
    base_url = get_dify_base_url()
    return f"{base_url.rstrip('/')}/{relative_url.lstrip('/')}"


def download_file_from_url(file_url: str) -> bytes:
    """下载 Dify 文件签名直链的内容。

    该链接自带签名鉴权（timestamp + nonce + sign），不需要额外的 API Key，
    但具有短时效性，必须在拿到 URL 后立即下载，否则会因签名过期返回 404。

    Args:
        file_url: Dify 传来的相对路径或完整 URL

    Returns:
        文件二进制内容

    Raises:
        ValueError: 下载失败（网络错误、签名过期、文件不存在等）
    """
    full_url = build_full_file_url(file_url)

    try:
        response = requests.get(full_url, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        raise ValueError(
            f"Failed to download file from Dify: {str(e)}. "
            f"该链接为短时效签名直链，若长时间未下载可能已过期。"
        )


def detect_file_format(file_name: str) -> str:
    """检测文件格式。

    Args:
        file_name: 文件名（含扩展名）

    Returns:
        格式名称：csv, xlsx, parquet, json

    Raises:
        ValueError: 不支持的格式
    """
    ext = Path(file_name).suffix.lower()

    format_map = {
        ".csv": "csv",
        ".xlsx": "xlsx",
        ".xls": "xlsx",
        ".parquet": "parquet",
        ".pq": "parquet",
        ".json": "json",
    }

    if ext not in format_map:
        raise ValueError(
            f"Unsupported file format: {ext}. "
            f"Supported: csv, xlsx, xls, parquet, json"
        )

    return format_map[ext]


def read_file_content(
    file_content: bytes,
    file_format: str,
) -> pd.DataFrame:
    """读取文件内容成 DataFrame。

    Args:
        file_content: 文件二进制内容
        file_format: 文件格式

    Returns:
        pandas DataFrame

    Raises:
        ValueError: 读取失败或格式错误
    """
    try:
        if file_format == "csv":
            return pd.read_csv(BytesIO(file_content))
        elif file_format == "xlsx":
            return pd.read_excel(BytesIO(file_content))
        elif file_format == "parquet":
            return pd.read_parquet(BytesIO(file_content))
        elif file_format == "json":
            return pd.read_json(BytesIO(file_content))
        else:
            raise ValueError(f"Unknown file format: {file_format}")
    except Exception as e:
        raise ValueError(f"Failed to read file: {str(e)}")


def validate_dataframe(df: pd.DataFrame) -> None:
    """验证 DataFrame 是否为有效的表格数据。

    Args:
        df: 数据框

    Raises:
        ValueError: 验证失败
    """
    if df.empty:
        raise ValueError("Imported file is empty")

    if len(df.columns) == 0:
        raise ValueError("File has no columns")


def import_data(
    file_url: str,
    file_name: str,
    conversation_id: str,
    workspace_root: str | Path = "workspace",
) -> DataImportResponse:
    """导入数据文件。

    Args:
        file_url: Dify 文件签名直链（相对路径）
        file_name: 原始文件名
        conversation_id: 会话 ID
        workspace_root: workspace 根目录
    """
    try:
        file_format = detect_file_format(file_name)
        file_content = download_file_from_url(file_url)
        file_size_mb = len(file_content) / 1024 / 1024

        df = read_file_content(file_content, file_format)
        validate_dataframe(df)

        workspace = Path(workspace_root) / conversation_id / "raw"
        workspace.mkdir(parents=True, exist_ok=True)

        output_filename = Path(file_name).stem + ".parquet"
        output_path = workspace / output_filename

        df.to_parquet(output_path, index=False)

        dataset_path = f"raw/{output_filename}"
        preview_data = df.head(5).to_dict(orient="records")

        return DataImportResponse(
            status="success",
            dataset_path=dataset_path,
            rows=len(df),
            columns=len(df.columns),
            column_names=[str(col) for col in df.columns.tolist()],
            preview_data=preview_data,
            file_size_mb=float(file_size_mb),
        )

    except ValueError as e:
        return DataImportResponse(
            status="error", error_message=str(e), dataset_path="",
            rows=0, columns=0, column_names=[], preview_data=[], file_size_mb=0.0,
        )
    except Exception as e:
        return DataImportResponse(
            status="error", error_message=f"Unexpected error: {str(e)}", dataset_path="",
            rows=0, columns=0, column_names=[], preview_data=[], file_size_mb=0.0,
        )