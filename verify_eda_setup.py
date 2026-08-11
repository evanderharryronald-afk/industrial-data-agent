"""
快速验证脚本：
1. 创建示例数据集
2. 启动 FastAPI 服务
3. 测试 EDA endpoint
4. 输出 Dify 集成所需的 OpenAPI schema

使用方式：
  python verify_eda_setup.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import requests

# 创建示例数据集
def setup_sample_data():
    """创建示例数据和 workspace 目录。"""
    workspace_root = Path("workspace")
    workspace_root.mkdir(exist_ok=True)
    
    # 创建测试 conversation 目录
    test_conv_dir = workspace_root / "test-conv-001"
    test_conv_dir.mkdir(exist_ok=True)
    
    # 创建必要的子目录
    for subdir in ["raw", "processed", "plots", "results"]:
        (test_conv_dir / subdir).mkdir(exist_ok=True)

    # 创建示例 CSV 数据
    sample_data = {
        "age": [25, 30, 35, None, 45, 50, 55, 60, 65, 70],
        "salary": [30000, 45000, 55000, 60000, 75000, 85000, 95000, 105000, 115000, 125000],
        "experience": [1, 3, 5, 7, 10, 12, 15, 18, 20, 22],
        "department": ["HR", "IT", "HR", "IT", "Finance", "IT", "HR", "Finance", "IT", "HR"],
        "performance_score": [7.5, 8.2, 8.8, None, 9.1, 8.5, 8.9, 9.3, 9.0, 8.7],
    }

    df = pd.DataFrame(sample_data)
    
    # 保存到 conversation 目录下的 raw 文件夹
    csv_path = test_conv_dir / "raw" / "sample_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"✅ 示例数据已创建：{csv_path}")

    # 创建示例 Parquet 数据
    parquet_path = test_conv_dir / "raw" / "sample_data.parquet"
    df.to_parquet(parquet_path, index=False)
    print(f"✅ 示例 Parquet 数据已创建：{parquet_path}")
    
    # 也在根目录保留一份（为了向后兼容早期测试）
    csv_root = workspace_root / "sample_data.csv"
    df.to_csv(csv_root, index=False)
    parquet_root = workspace_root / "sample_data.parquet"
    df.to_parquet(parquet_root, index=False)

    return csv_path, parquet_path


def test_eda_endpoint():
    """测试 EDA endpoint。"""
    print("\n" + "=" * 60)
    print("测试 EDA Endpoint")
    print("=" * 60)

    # 确保 FastAPI 服务已启动
    try:
        health = requests.get("http://localhost:8000/health", timeout=2)
        health.raise_for_status()
    except Exception as e:
        print(f"❌ FastAPI 服务未启动，请运行：python -m tools.main")
        print(f"   或在另一个终端运行：uvicorn tools.main:app --reload")
        sys.exit(1)

    # 测试 1：基础 EDA
    print("\n📌 测试 1：基础 EDA（无目标列）")
    request_payload = {
        "conversation_id": "test-conv-001",
        "dataset_path": "raw/sample_data.csv",
        "detail_level": "basic",
    }
    response = requests.post(
        "http://localhost:8000/api/v1/tools/eda/analyze",
        json=request_payload,
        timeout=10,
    )
    result = response.json()

    print(f"Status Code: {response.status_code}")
    print(f"Response Status: {result['status']}")

    if result["status"] == "success":
        print(f"✅ 数据集形状：{result['dataset_shape']}")
        print(f"✅ 列数：{len(result['columns'])}")
        print(f"✅ 内存占用：{result['memory_usage_mb']:.2f} MB")
        print(f"✅ 警告数：{len(result['warning_messages'])}")
        if result["warning_messages"]:
            print("   警告信息：")
            for warn in result["warning_messages"]:
                print(f"   - {warn}")
    else:
        print(f"❌ Error: {result['error_message']}")

    # 测试 2：带目标列的 EDA
    print("\n📌 测试 2：EDA（指定目标列）")
    request_payload = {
        "conversation_id": "test-conv-001",
        "dataset_path": "raw/sample_data.csv",
        "target_column": "salary",
        "detail_level": "basic",
    }
    response = requests.post(
        "http://localhost:8000/api/v1/tools/eda/analyze",
        json=request_payload,
        timeout=10,
    )
    result = response.json()

    if result["status"] == "success":
        if result["target_column_info"]:
            print(f"✅ 目标列 'salary' 信息已返回：")
            target_info = result["target_column_info"]
            print(f"   - 缺失率：{target_info['missing_rate']:.2%}")
            print(f"   - 唯一值个数：{target_info['unique_count']}")
        else:
            print("❌ 目标列信息为空")
    else:
        print(f"❌ Error: {result['error_message']}")

    # 测试 3：Parquet 格式
    print("\n📌 测试 3：EDA（Parquet 格式）")
    request_payload = {
        "conversation_id": "test-conv-001",
        "dataset_path": "raw/sample_data.parquet",
        "detail_level": "basic",
    }
    response = requests.post(
        "http://localhost:8000/api/v1/tools/eda/analyze",
        json=request_payload,
        timeout=10,
    )
    result = response.json()

    if result["status"] == "success":
        print(f"✅ Parquet 格式读取成功，行数：{result['dataset_shape'][0]}")
    else:
        print(f"❌ Error: {result['error_message']}")

    # 测试 4：不存在的文件
    print("\n📌 测试 4：错误处理（不存在的文件）")
    request_payload = {
        "conversation_id": "test-conv-001",
        "dataset_path": "raw/nonexistent.csv",
    }
    response = requests.post(
        "http://localhost:8000/api/v1/tools/eda/analyze",
        json=request_payload,
        timeout=10,
    )
    result = response.json()

    if result["status"] == "error":
        print(f"✅ 错误处理正常：{result['error_message']}")
    else:
        print(f"❌ 应该返回 error status")


def get_openapi_schema():
    """获取 OpenAPI schema，用于 Dify 集成。"""
    print("\n" + "=" * 60)
    print("OpenAPI Schema（用于 Dify 集成）")
    print("=" * 60)

    try:
        response = requests.get("http://localhost:8000/openapi.json", timeout=5)
        response.raise_for_status()
        schema = response.json()

        # 提取 EDA endpoint 的 schema
        if "/api/v1/tools/eda/analyze" in schema["paths"]:
            eda_schema = schema["paths"]["/api/v1/tools/eda/analyze"]["post"]
            print("\n✅ EDA Endpoint 的 OpenAPI Schema：")
            print(json.dumps(eda_schema, indent=2, ensure_ascii=False))

            # 保存 schema 到文件，便于后续导入 Dify
            schema_file = Path("eda_openapi_schema.json")
            with open(schema_file, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Schema 已保存到：{schema_file}")
        else:
            print("❌ 未找到 EDA endpoint")

    except Exception as e:
        print(f"❌ 获取 OpenAPI Schema 失败：{e}")


def print_instructions():
    """打印使用说明。"""
    print("\n" + "=" * 60)
    print("🚀 接下来的步骤")
    print("=" * 60)
    print("""
1. 启动 FastAPI 服务：
   在另一个终端运行：
   uvicorn tools.main:app --reload --port 8000

2. 验证 EDA endpoint：
   运行此脚本：
   python verify_eda_setup.py

3. 在 Dify 中集成 EDA 工具：
   - 打开 Dify Web UI
   - 创建新的 Workflow
   - 在 Tools 中重新导入 OpenAPI Schema（更新后会用 conversation_id）
   - 测试 EDA 工具调用，确保能接收 Dify 的 conversation_id

4. 测试 Dify 集成：
   在 Dify Workflow 中设置：
   - Input: dataset_path (Text)
   - Tool: EDA Analysis，绑定 dataset_path 参数
   - 执行，验证 conversation_id 是否正确传递并隔离文件
    """)


if __name__ == "__main__":
    print("🔧 工业数据处理智能体 - EDA 工具验证脚本\n")

    # 第一步：创建示例数据
    print("=" * 60)
    print("准备示例数据")
    print("=" * 60)
    setup_sample_data()

    # 第二步：测试 EDA endpoint（如果服务已启动）
    try:
        test_eda_endpoint()
    except Exception as e:
        print(f"\n⚠️  跳过 endpoint 测试（服务可能未启动）：{e}")

    # 第三步：获取 OpenAPI schema
    try:
        get_openapi_schema()
    except Exception as e:
        print(f"\n⚠️  跳过 schema 获取（服务可能未启动）：{e}")

    # 第四步：打印后续步骤
    print_instructions()
