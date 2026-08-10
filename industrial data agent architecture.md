# 工业数据处理智能体 — 新项目实施计划

## 项目定位

- **新开独立项目**，与现有 `steel-agent-tools` 分开，避免新技术栈（LangGraph、本地代码沙箱）污染已验证的主线。
- **不替代**现有 Dify + FastAPI 架构，而是作为其中一个"复杂 tool"背后的子系统：
  - Dify：对话入口、权限、历史记录（不变）
  - FastAPI：确定性工具（EDA / 相关性分析 / Optuna / SHAP）+ 对外暴露 LangGraph 子系统的接口
  - LangGraph：仅用于"数据清洗 / 特征工程"这类需要现场生成代码、多步试错、可能失败重试的环节
- **总体顺序**：先验证工具链路（低风险），再验证代码生成 + 沙箱执行（高风险），最后打通自纠错循环。不同时啃两块陌生技术。
- **数据安全**：LLM 现场生成清洗代码时，传给 LLM 的 schema / 报错日志 / 样例数据要过一遍脱敏检查，确认走本地 Ollama 而非云端 API，或云端 API 只接触脱敏后的字段名与统计摘要。

---

## Phase 0：项目脚手架（0.5 天）

**目标**：建好独立项目结构，不写业务逻辑。结构从一开始就按"可扩展"设计，避免后续推倒重来。

- 新建项目目录，例如 `industrial-data-agent/`
- 目录结构建议：
  ```
  industrial-data-agent/
  ├── tools/
  │   ├── main.py              # 单进程，挂载所有工具的 router（当前阶段的部署方式）
  │   ├── eda/
  │   │   ├── router.py         # HTTP 层
  │   │   ├── service.py        # 业务逻辑（纯函数，不依赖 FastAPI）
  │   │   ├── schemas.py        # pydantic 请求/响应模型
  │   │   └── requirements.txt  # 记录该模块依赖，便于未来单独拆分时直接抽取
  │   ├── correlation/
  │   │   ├── router.py
  │   │   ├── service.py
  │   │   └── schemas.py
  │   ├── optuna_tuning/
  │   │   ├── router.py
  │   │   ├── service.py
  │   │   └── schemas.py
  │   ├── train/
  │   │   ├── router.py
  │   │   ├── service.py
  │   │   └── schemas.py
  │   └── shap_explain/
  │       ├── router.py
  │       ├── service.py
  │       └── schemas.py
  ├── graph/
  │   ├── pipelines/
  │   │   └── rh_cleaning/        # 第一个场景专属：状态/节点/边/构图，四件套
  │   │       ├── state.py
  │   │       ├── nodes.py
  │   │       ├── edges.py
  │   │       └── builder.py
  │   ├── common/
  │   │   ├── nodes.py            # 跨 pipeline 复用的节点（如统一校验断言）
  │   │   └── tool_client.py      # 统一封装对 tools/ 服务的 HTTP 调用
  │   └── registry.py             # 汇总所有 pipeline，按 pipeline_name 路由，对外统一入口
  ├── sandbox/                    # 本地代码执行沙箱（Phase 3+ 才填）
  ├── workspace/                  # session_id 下的数据文件缓存
  ├── shared/                     # 跨 tools/graph 共用的 schema 定义、文件读写工具
  └── tests/
  ```

**两条结构设计原则（贯穿全项目）**：

1. **`tools/` 的部署方式与代码组织方式分离**：当前用单进程 + `APIRouter` 按模块拆分（代码模块化，但只跑一个进程，避免"很多服务同时空跑"的资源顾虑）。只有当某个工具出现依赖冲突（如不同库要求不同版本的 numpy），或需要独立的资源隔离/超时控制（如 Optuna 长时间调参），才把它单独拆成独立部署的服务，不用一次性全拆。每个模块下的 `requirements.txt` 从现在就写好，方便未来"拆分"只是把文件夹搬走，不用重新梳理依赖。
2. **`graph/` 从一开始按"多状态图共存"设计**：`pipelines/` 下每个场景（RH 炉清洗、未来的氧气吹炼预测等）各自一套独立的 state / nodes / edges / builder，互不牵连；新增一个全新场景 = 新建一个 pipeline 文件夹，不影响已有的图。真正通用的节点（如数据校验断言）沉淀到 `common/`，被多个 pipeline 复用。`registry.py` 作为唯一对外入口，FastAPI 调用时带 `pipeline_name` 参数路由到对应的图，Dify 侧不需要感知内部有几个图、几个节点。

- 数据传递规范：所有工具之间通过 `workspace/{session_id}/xxx.parquet` 文件句柄传递，不通过对话变量塞数据。`session_id` 可直接用 Dify 对话自带的 conversation_id，或调用时生成一个 UUID，工具读写文件都走这个路径，足以支撑 Phase 1-2 的验证目标。持久化现阶段就是"文件写在磁盘上不删"，不需要额外的产出物注册表或数据库——这类东西属于"以后需要时可以在文件路径规范之上新增一层，不影响现有工具代码"的可逆决策，不必现在设计。

**工具内部三层拆分（`router.py` / `service.py` / `schemas.py`）**：

每个工具目录内部固定拆三层，不要把逻辑全堆进 `router.py`：

- `router.py`：仅负责 HTTP 层——接收请求、调用 `service.py`、返回响应，不写业务逻辑
- `service.py`：真正的业务逻辑（如调用 ydata-profiling），是不依赖 FastAPI 的纯 Python 函数，方便单元测试，也方便未来被 `graph/common/tool_client.py` 直接复用或整体搬去独立部署
- `schemas.py`：用 pydantic 定义该工具的请求/响应模型，字段要写清楚 `Field(description=...)`——这段描述是 LLM 判断"该不该调这个工具、参数怎么填"的依据，写得含糊会导致误调用

**为什么按工具垂直分（而不是按 router/service/schema 类型横向分成三个文件夹）**：改动一个工具时只需要盯着它自己的文件夹，不用跨目录跳转；后续某个工具要单独拆分部署时，整个文件夹搬走即可，天然可拆分。这也是"按可能一起改、一起搬的东西分组"这一目录设计原则的体现。

**关于 Dify 侧的 schema 调用问题**：不需要额外设计一个"全局统一 schema"。FastAPI 会根据每个 router 里的 pydantic 模型，自动生成一份包含所有工具各自独立 schema 的 OpenAPI 文档（`/openapi.json`）。Dify 导入这份文档时，会把每个 path（每个工具）解析成独立的 Tool Action，LLM 看到的依然是每个工具各自明确的参数说明，不会互相混淆。不需要手写 OpenAPI yaml，用 FastAPI 自动生成即可，避免和代码实际行为不同步。

---

---

## Schema 设计原则（贯穿全项目，先读完这节再开始写 Phase 1 代码）

Schema 不只是接口的数据格式定义，它是 **LLM 判断"该不该调这个工具、参数怎么填"的唯一依据**——LLM 看不到你的 Python 代码，只能读 FastAPI 自动生成的 OpenAPI 文档里的字段名、类型、description。这节把项目里所有会用到 schema 设计的地方列清楚，作为后续各 Phase 写代码时的对照标准。

### 通用原则

1. **暴露给 LLM 的字段禁止用 `dict` / `Any` 兜底**，务必用明确类型 + `Field(description=...)`。LLM 只能靠自然语言描述判断怎么填，写得含糊会导致误调用或参数缺失。
2. **每个字段的 description 要交代"这个值通常从哪来"**，尤其是文件路径类字段（如"通常来自上一步 clean_data 工具的返回值"），这能显著提升 LLM 串联多个工具调用的准确率。
3. **request 和 response 都要设计**，不要只顾着写清楚入参、放任返回结构随意——response 是 LLM 向用户总结结果、以及后续节点消费数据的依据。

### 公共 BaseSchema（`shared/base_schemas.py`）

几乎所有工具的 request 都有 `session_id`/`workspace_id`，response 都有 `status`/`error_message`。抽成基类，各工具 schema 继承，避免重复定义，也方便以后统一加字段：

```python
# shared/base_schemas.py
class ToolRequestBase(BaseModel):
    session_id: str = Field(description="当前会话/workspace的唯一标识，用于定位 workspace/{session_id}/ 下的文件")

class ToolResponseBase(BaseModel):
    status: Literal["success", "error"]
    error_message: str | None = None
    metadata: dict = Field(default_factory=dict, description="预留字段，装暂不确定是否需要固化为正式字段的辅助信息")
```

### 项目里每个涉及 schema 设计的位置一览

| 位置 | Schema 设计要点 |
|---|---|
| `tools/eda/schemas.py` | Request 相对固定：`dataset_path`、可选 `target_column`。Response 除报告文件路径外，把关键元特征（列名/类型/缺失率）结构化返回，方便 LLM 直接总结成话，不用再解析报告文件 |
| `tools/correlation/schemas.py` | Request 需要 `dataset_path` + 目标列；若支持多种相关性方法（pearson/spearman），用 `Literal` 限定，不要开放成自由字符串 |
| `tools/optuna_tuning/schemas.py` | **重点对象**：参数搜索空间天然是嵌套/可变结构。用 `model_type: Literal[...]` 约束 + description 里写清楚每种类型下 `search_space` 支持哪些字段，不要给 LLM 一个完全开放的 dict。返回结构要包含最优超参 + 对应的模型文件路径 |
| `tools/train/schemas.py` | 同上，`model_type: Literal["xgboost","lightgbm","linear",...]` 决定 `hyperparameters: dict` 里可用字段，具体字段清单写进 description。新增模型类型时只扩展 `Literal` 和 description，不用改结构 |
| `tools/shap_explain/schemas.py` | Response 是长期会扩展的对象（未来可能加交互作用图等新分析类型），核心字段（如 `feature_importance: dict`）保持稳定，新增能力优先加进 `metadata`，不要改已有字段的类型/含义 |
| `graph/pipelines/*/state.py` | 这不是对外 API schema，但同样是"一份清楚的契约"——`DataAgentState` 里每个字段的类型、用途要注释清楚，因为 LangGraph 节点之间全靠这个 State 传递上下文，字段含糊会导致节点间数据传递出错 |
| `graph/registry.py` 对外的 `POST /api/v1/agent/start` 等 endpoint | 这是 Dify 侧唯一注册的 Tool，其 schema 需要包含 `pipeline_name: Literal["rh_cleaning", "oxygen_blowing", ...]`，新增 pipeline 时在这里加一个枚举值即可；`approve` 接口的 schema 要能表达"确认/拒绝/修改后继续"这几种人工干预结果，不要只做布尔值，未来人工反馈的粒度大概率会变细 |
| Dify 侧 | 不需要单独设计，FastAPI 自动生成的 OpenAPI 文档已经把每个工具的 schema 分别暴露成独立 Tool Action，Dify 导入即可，不用手写 |

### 扩展新工具/新场景时，schema 该怎么加

- **新增一个简单确定性工具**（如异常值检测）：照抄 EDA/correlation 的模式，request 用具体字段，不引入新的设计问题
- **新增一个"参数空间可变"类工具**（如未来可能的自动特征选择）：照抄 optuna/train 的 `xxx_type: Literal + 受控 dict` 模式，避免每加一种子类型就重新设计一次 schema
- **新增一个 pipeline**：只需要在 `pipelines/{new_pipeline}/state.py` 里定义该场景专属的 State（不影响其他 pipeline），并在 `registry.py` 的 `pipeline_name` 枚举里加一项，对外 API schema 基本不用改

---

## Phase 1：确定性工具 + Dify 集成验证（顺序 A，预计 3–5 天）

**目标**：验证"LLM 调度是否可靠、Dify 的 tool-call 链路是否 work"，不涉及 LangGraph、不涉及代码沙箱。这是当前最该做的第一步。

### 步骤 1.1：选 1–2 个工具打样

- 优先选 **EDA + 相关性分析**（你已熟悉，成熟库直接封装，无需 LLM 生成代码）
- `tools/eda/`：`schemas.py` 定义输入 `dataset_path`、输出报告路径+关键元特征（列名、类型、缺失率）；`service.py` 封装 ydata-profiling 的调用逻辑；`router.py` 接收请求转发给 service
- `tools/correlation/`：`schemas.py` 定义输入 `dataset_path` + 目标列；`service.py` 封装 pandas/scipy 计算逻辑；`router.py` 转发

### 步骤 1.2：用 FastAPI 包装

- 在 `tools/main.py` 里创建一个 app，把 `eda/router.py`、`correlation/router.py` 用 `include_router()` 挂载进去，单进程跑，不需要各自起独立服务
- 每个 endpoint 输入输出走 `workspace_id` + 文件路径，不直接传大数据
- 本地起服务，先用 Postman/curl 手动验证输入输出正确，并检查 `/docs` 页面里每个工具的 schema 描述是否清楚（这份文档后续会直接喂给 Dify）

### 步骤 1.3：注册进 Dify 自定义 Tool

- 用 OpenAPI schema 描述这两个 tool，注册进本地 Dify 实例
- 建一个简单的 Dify Agent，测试："帮我看看这份数据的分布情况" → 能否正确调用 `run_eda_tool` 并返回可读结果

### 步骤 1.4：验证要点（这一步的核心产出）

- LLM 能否正确判断该调哪个 tool、参数传得对不对
- 返回结果（尤其是图片/报告类）能否在 Dify 界面正常展示
- 记录下调用失败/参数错误的典型情况，作为后续 Prompt 调优的输入

**验收标准**：端到端跑通"用户提问 → Dify 调 FastAPI tool → 拿到结构化结果 → LLM 总结成人话"，无需人工干预修数据格式。

---

## Phase 2：补全确定性工具集（预计 3–5 天）

**目标**：在 Phase 1 验证的模式下，扩充工具覆盖面，为后续建模/调参/解释性分析打基础。

- `tools/optuna_tuning/router.py`：输入预定义参数空间配置，自动跑多轮 Tuning，返回最优超参 + 模型文件路径
- `tools/train/router.py`：常规建模（sklearn/xgboost/lightgbm），输入特征数据路径 + 目标列，输出模型文件
- `tools/shap_explain/router.py`：读取模型 + 测试数据，输出变量重要性图表 + Feature Importance JSON
- 全部按 Phase 1 的模式挂进 `tools/main.py`：router 编写 → workspace 文件传递 → 注册 Dify Tool → 手测
- **资源观察点**：Optuna 调参耗时较长，先在单进程模式下跑，若发现执行期间明显拖慢其他工具的响应（阻塞主进程），再考虑把这一个工具单独拆成独立部署的服务，或接入任务队列（如 Celery）做异步执行，不用现在就上

**验收标准**：一次对话内能完成"EDA → 相关性分析 → 训练模型 → 调参 → SHAP 解释"的完整确定性链路（数据清洗/特征工程环节先用手工脚本准备好数据，不接入 LLM 生成代码）。

---

## Phase 3：本地代码沙箱 + LangGraph 状态图（顺序 B，预计 1–2 周）

**目标**：解决"数据聚合/清洗/特征工程"这类无法用确定性工具覆盖的环节——需要 LLM 现场生成代码。这是全项目最难、最该放在后面做的部分。

### 步骤 3.1：搭一个最小沙箱，不追求完整 Docker 方案

- 先用**受限 subprocess + resource 限制**（限制内存、超时、文件系统访问范围）跑通"LLM 生成代码 → 本地执行 → 返回结果/报错"这个最小闭环
- 参考 **Open Interpreter**（OpenInterpreter/open-interpreter）的本地沙箱执行和报错处理部分代码，重点抄它"生成代码→本地执行→捕获报错→重新生成"这套逻辑的实现，不需要整体引入这个项目做外壳
- 如果后续要更贴合 LangGraph 生态，可以换成 **LangChain Sandbox（PyodideSandbox）**，这是官方配套的轻量沙箱组件

### 步骤 3.2：定义第一个 pipeline —— `graph/pipelines/rh_cleaning/`

在 `graph/pipelines/rh_cleaning/state.py` 中定义该场景专属的 State（未来新增场景如氧气吹炼预测，会在 `pipelines/oxygen_blowing/state.py` 里独立定义，互不影响）：

```python
class RHCleaningState(TypedDict):
    session_id: str
    raw_data_path: str
    current_data_path: str
    schema_info: dict
    current_step: str
    code_history: List[str]
    execution_logs: List[str]
    metrics: dict
    retry_count: int
```

### 步骤 3.3：搭建单一状态图，先只做"清洗"这一个节点

- 不要一次性把清洗 + 特征工程 + 自纠错全部铺开
- 在 `graph/pipelines/rh_cleaning/nodes.py` 里写 `Data Prep Node` — LLM 生成清洗代码 → 丢进 Phase 3.1 的沙箱执行 → 更新 `current_data_path`
- 在 `graph/pipelines/rh_cleaning/builder.py` 中组装成 compiled graph
- 暂不加自纠错分支，先验证"LLM 生成代码 + 沙箱执行"这条链路本身能不能稳定跑通
- 需要复用已有确定性工具时（如清洗中调用统计校验），通过 `graph/common/tool_client.py` 统一封装的 HTTP client 调用 `tools/` 里的服务，不在节点内部重复实现

### 步骤 3.4：参考资料

- **LangGraph 官方仓库示例**（langchain-ai/langgraph），重点看带 `error handling / retry` 关键词的官方示例，这是持续维护的一手资料，比第三方教程可靠
- 不再参考 TaskWeaver（已于 2026 年 3 月被官方归档，不再维护，仅作历史设计思路参考，不做代码依赖）

**验收标准**：给一份真实/模拟的脏数据，LLM 能生成可执行的清洗代码，在本地沙箱跑出干净数据，人工检查结果基本合理。

---

## Phase 4：过程校验与自纠错闭环（预计 1 周）

**目标**：解决"LLM 写的代码报错"或"清洗后数据异常"的质量控制问题。这一步建立在 Phase 3 稳定跑通之后。

### 步骤 4.1：过程级断言（Validation Edge）

沙箱代码运行后自动追加校验：

- 是否产生全空列
- 行数是否异常骤减（如丢失超过 50% 数据）
- 目标列（Target）是否存在缺失值

这类校验逻辑与具体场景无关，属于跨 pipeline 复用的能力，写在 `graph/common/nodes.py` 里作为通用校验节点，`rh_cleaning` 和未来的 `oxygen_blowing` pipeline 都可以直接引用，不用各自重复实现。

### 步骤 4.2：Self-Correction Retry Loop

- 沙箱报错或校验断言失败时：把 Error Log + 上一步代码 + 当前 Schema 重新丢给 LLM
- Prompt："代码运行出错/数据校验未通过，请根据报错日志修正你的 Python 代码"
- 最多重试 3 次，超过则终止并返回人工介入提示，防止死循环

### 步骤 4.3：条件边（Conditional Edges）

- 例：建模完成后检查 `metrics['R2']`，若 < 0.85 且 `retry_count < 3`，路由回 Feature Eng Node 重新派生特征

**验收标准**：故意构造几个会报错/会产生异常数据的场景，验证自纠错能在 3 次重试内收敛，或正确地放弃并提示人工介入。

---

## Phase 5：特征工程节点 + API 封装（预计 1 周）

**目标**：把特征工程环节接入状态图，并把整个 LangGraph 引擎暴露给 Dify。

- Feature Eng Node：简单规则用 LLM 生成代码，时序特征提取直接调用已封装的 tsfresh 工具（不必事事都靠 LLM 现场生成），仍加进 `rh_cleaning` pipeline 内
- 在 `graph/registry.py` 中注册 `rh_cleaning` pipeline（`{"rh_cleaning": rh_cleaning_builder.compiled_graph}`），为未来新增场景预留统一入口
- FastAPI 封装 LangGraph 执行入口为 RESTful API / WebSocket（支持流式输出节点状态日志），入口内部通过 `pipeline_name` 参数查 registry 路由到对应的图
- 暴露 Endpoint：
  - `POST /api/v1/agent/start`（body 含 `pipeline_name`，如 `"rh_cleaning"`）
  - `POST /api/v1/agent/approve`（Human-in-the-loop 人工确认节点）
  - `GET /api/v1/agent/status/{session_id}`
- 在 Dify 中注册为**一个** Custom Tool（`run_data_pipeline_agent`），指向上述 FastAPI 接口；未来新增 pipeline 只需在 registry 里多注册一条，Dify 侧完全无感知，不需要新增 Tool

**验收标准**：从 Dify 发起一次完整请求，能触发"清洗 → 特征工程 → 训练 → 评估"的多步执行，中途人工可介入确认，最终返回结果摘要 + SHAP 图。

---

## 阶段总览

| 阶段 | 内容 | 预计时间 | 风险等级 |
|---|---|---|---|
| Phase 0 | 项目脚手架 | 0.5 天 | 低 |
| Phase 1 | 确定性工具打样 + Dify 集成验证 | 3–5 天 | 低（核心验证目标） |
| Phase 2 | 补全确定性工具集 | 3–5 天 | 低 |
| Phase 3 | 本地沙箱 + LangGraph 单节点（清洗） | 1–2 周 | 高（新技术栈） |
| Phase 4 | 校验断言 + 自纠错闭环 | 1 周 | 高 |
| Phase 5 | 特征工程节点 + API 封装 | 1 周 | 中 |

**关键原则重申**：Phase 1–2 不涉及任何新技术栈，只验证集成方式，出问题好排查；Phase 3 才第一次引入 LangGraph 和沙箱，且刻意只做"清洗"一个节点，不与自纠错逻辑耦合调试；自纠错和条件回滚放到 Phase 4，等基础链路稳定后再叠加复杂度。

---

## 扩展性说明（未来新增功能时如何操作）

| 场景 | 操作 |
|---|---|
| 新增一个确定性工具（如异常值检测） | 在 `tools/` 下新建模块文件夹 + `router.py`，在 `main.py` 里挂载，写 OpenAPI schema 注册进 Dify |
| 某个工具出现依赖冲突或需要独立资源隔离 | 把该模块文件夹整体搬出，独立起 FastAPI app + Dockerfile，`requirements.txt` 已提前写好，直接复用 |
| 新增一个全新业务场景（如氧气吹炼预测的清洗/建模流程） | 在 `graph/pipelines/` 下新建文件夹（如 `oxygen_blowing/`），复制 `rh_cleaning/` 的四件套结构改写，在 `registry.py` 里多注册一条 |
| 新场景需要复用已有场景的某个节点 | 把该节点从原 pipeline 中提取到 `graph/common/nodes.py`，两边都引用它 |
| Dify 侧需要感知/单独调用某个 graph 内部节点 | 需要额外把该节点单独暴露成一个 tool 注册进 Dify，这是主动设计选择，不会随目录新增自动发生 |
