# industrial-data-agent

工业数据处理智能体 — 独立于 `steel-agent-tools` 的新项目。
架构背景与分 Phase 计划见设计文档，本 README 只记录当前已实现的状态。

## 当前状态：Phase 0 已完成

- 目录骨架已按设计文档搭好。
- `shared/base_schemas.py`：`ToolRequestBase` / `ToolResponseBase` 已实现。
- `graph/`、`sandbox/` 仅有目录占位（含 `.gitkeep`），无业务代码，等 Phase 3+ 再填。
- `tools/eda/`、`tools/correlation/` 目前是空目录，Phase 1 才会填 router/service/schemas。
- `tools/optuna_tuning/`、`tools/train/`、`tools/shap_explain/` 是空目录，Phase 2 才会填。

## 目录结构

```
industrial-data-agent/
├── tools/
│   ├── main.py              # (Phase 1 才创建) 单进程 FastAPI，挂载所有工具 router
│   ├── eda/                 # (Phase 1 填充) router.py / service.py / schemas.py
│   ├── correlation/         # (Phase 1 填充)
│   ├── optuna_tuning/       # (Phase 2 占位)
│   ├── train/                # (Phase 2 占位)
│   └── shap_explain/        # (Phase 2 占位)
├── graph/                    # (Phase 3+ 占位，当前无代码)
│   ├── pipelines/rh_cleaning/
│   ├── common/
│   └── registry.py           # (Phase 5 才创建)
├── sandbox/                  # (Phase 3+ 占位)
├── workspace/                 # session_id 下的数据文件缓存，不入库
├── shared/
│   └── base_schemas.py       # 已实现：ToolRequestBase / ToolResponseBase
└── tests/
```

## 本地环境搭建（Windows 11 + PyCharm，python 3.11.9）

```powershell
# 在项目根目录下创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

Phase 1 完成后，`tools/main.py` 会用如下方式启动：

```powershell
uvicorn tools.main:app --reload --port 8000
```

启动后访问 `http://127.0.0.1:8000/docs` 查看自动生成的 OpenAPI 文档，
这份文档后续会直接导入本地 Dify 注册为 Custom Tool。
