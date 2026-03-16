# TechHub 智能客服 Agent 系统

基于 LangGraph + LangChain + LangSmith 构建的企业级多 Agent 智能客服系统，以虚拟电商品牌 **TechHub** 为背景，覆盖从 Agent 开发、离线评估、生产部署到持续优化的完整 AI 工程生命周期。

<div align="center">
    <img src="images/main_graphic.png">
</div>

---

## 🚀 立即体验

| 服务 | 地址 |
|------|------|
| 💬 聊天界面 | https://aiagent-self.vercel.app |
| 🔌 API 文档 | https://aiagent-production.up.railway.app/docs |

### 如何使用

#### 一、通用咨询（无需登录）

直接提问，系统通过 RAG 检索产品文档与政策文件作答。

**商品咨询**
- `"MacBook Pro 有哪些 USB-C 接口？"`
- `"推荐一款适合家用的 4K 显示器"`
- `"机械键盘和薄膜键盘哪个更适合办公？"`
- `"这款耳机支持主动降噪吗？"`

**政策咨询**
- `"你们的退货政策是什么？退货期限是多久？"`
- `"保修范围包括哪些情况？"`
- `"跨境运费怎么算？大概几天到？"`
- `"商品和配件的兼容性怎么确认？"`

**故障排查 / 使用指南**
- `"笔记本无法连接外接显示器怎么办？"`
- `"键盘驱动安装后不识别，如何解决？"`

---

#### 二、订单与账户查询（需要身份核验）

涉及个人订单或账户数据时，系统会自动暂停，提示验证邮箱：

> 系统会询问：**"请提供您的邮箱地址以完成身份核验"**
>
> 输入测试邮箱：`sarah.chen@gmail.com`（或 `marcus.johnson@yahoo.com`）即可完成验证。

**订单状态查询**
- `"我的订单到哪里了？"`
- `"ORD-2024-0088 现在什么状态？什么时候发货？"`

**历史订单查看**
- `"帮我查一下最近三笔订单"`
- `"我上次买了什么商品？"`

**消费数据分析**
- `"我今年在 TechHub 一共花了多少钱？"`
- `"我买过几台显示器？"`

---

## 系统架构

```
用户浏览器 (Next.js)
        ↓ HTTP
FastAPI 后端
  ├── 安全过滤 (prompt_guard)
  ├── 会话管理 (Redis)
  └── LangGraph Agent
        ├── 意图分类
        ├── 身份核验 HITL (interrupt)
        └── Supervisor 路由
              ├── SQL Agent → PostgreSQL / SQLite
              └── Docs Agent → 向量检索 (RAG)

监控层：Prometheus + Grafana
```

### 核心组件

| 组件 | 技术栈 | 端口 |
|------|--------|------|
| 前端聊天界面 | Next.js 14 (App Router) | 3000 |
| API 后端 | FastAPI + Uvicorn | 8000 |
| 数据库 | PostgreSQL 16 | 5432 |
| 缓存/会话 | Redis 7 | 6379 |
| 指标采集 | Prometheus | 9090 |
| 监控看板 | Grafana | 3001 |

---

## 快速启动（Docker）

### 前置条件

- Docker & Docker Compose
- API Keys: `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`，以及 `LANGSMITH_API_KEY`

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写以下必填项：
#   ANTHROPIC_API_KEY 或 OPENAI_API_KEY
#   LANGSMITH_API_KEY
#   POSTGRES_PASSWORD=techhub_dev   # 可选，有默认值
```

### 2. 启动全栈服务

```bash
# 首次启动（含构建镜像）
docker compose up --build

# 后续启动
docker compose up -d
```

### 3. 初始化数据（仅首次）

```bash
# 迁移 SQLite 数据到 PostgreSQL
docker compose run --rm api python data/migrations/migrate_sqlite_to_pg.py

# 构建向量检索库（~60秒）
docker compose run --rm -e PYTHONPATH=/app api python data/data_generation/build_vectorstore.py
```

### 4. 访问服务

- 聊天界面：http://localhost:3000
- API 文档：http://localhost:8000/docs
- Grafana 监控：http://localhost:3001（账号: admin / admin）
- Prometheus：http://localhost:9090

> **注意**：修改 `.env` 后使用 `docker compose up -d api` 重新加载，而非 `restart`。

---

## 本地开发（非 Docker）

```bash
# 安装依赖（自动创建 .venv）
uv sync

# 构建向量库
uv run python data/data_generation/build_vectorstore.py

# 启动 API
uv run uvicorn backend.main:app --reload --port 8000

# 启动前端
cd frontend && npm install && npm run dev

# 或启动 Jupyter（用于 Workshop 模块）
uv run jupyter lab
```

---

## 项目结构

```
aiagent/
├── agents/                          # Agent 工厂函数
│   ├── db_agent.py                  # 结构化数据库查询（固定工具）
│   ├── sql_agent.py                 # 灵活 SQL 生成（改进版）
│   ├── docs_agent.py                # RAG 文档检索
│   ├── supervisor_agent.py          # 多 Agent 协调器
│   └── supervisor_hitl_agent.py     # 完整系统（含身份核验）
│
├── backend/                         # FastAPI 后端
│   ├── main.py                      # 应用入口 + CORS + 路由注册
│   ├── metrics.py                   # Prometheus 自定义指标
│   ├── api/routes/
│   │   ├── chat.py                  # POST /api/v1/chat（流式支持）
│   │   ├── sessions.py              # 会话创建与管理
│   │   └── feedback.py              # 用户反馈收集
│   ├── services/
│   │   ├── agent_service.py         # LangGraph Agent 封装
│   │   └── session_service.py       # Redis 会话持久化
│   └── security/
│       └── prompt_guard.py          # 提示词注入检测 + 违禁词过滤
│
├── frontend/                        # Next.js 前端
│   └── app/
│       ├── page.tsx                 # 主页（含实时监控入口）
│       └── globals.css
│
├── tools/                           # Agent 工具
│   ├── database.py                  # 6 个数据库工具（订单/商品/SQL）
│   └── documents.py                 # 2 个 RAG 工具（商品/政策）
│
├── evaluators/                      # 评估器
│   └── evaluators.py                # LLM-as-judge + 工具调用计数器
│
├── deployments/                     # LangSmith 生产部署图
│   ├── db_agent_graph.py
│   ├── sql_agent_graph.py
│   ├── docs_agent_graph.py
│   ├── supervisor_agent_graph.py
│   ├── supervisor_hitl_agent_graph.py
│   └── supervisor_hitl_sql_agent_graph.py   # 推荐生产图
│
├── simulations/                     # 自动化压测与 Demo 系统
│   ├── run_simulation.py            # CLI 入口
│   ├── scenarios.json               # 10 个客户 Persona
│   ├── interrupt_handler.py         # HITL 中断自动处理
│   └── simulation_config.py         # 配置参数
│
├── monitoring/                      # 可观测性配置
│   ├── prometheus.yml
│   └── grafana/provisioning/
│
├── workshop_modules/                # 教学 Jupyter Notebooks
│   ├── module_1/                    # Agent 开发（4 节）
│   ├── module_2/                    # 评估与改进（2 节）
│   └── module_3/                    # 生产部署（2 节）
│
├── data/
│   ├── structured/techhub.db        # SQLite（50客户/25商品/250订单）
│   ├── documents/                   # 30 篇 Markdown 文档（RAG 语料）
│   ├── vector_stores/               # 预构建向量库
│   └── migrations/                  # PostgreSQL 迁移脚本
│
├── config.py                        # 全局配置（模型、路径、嵌入提供商）
├── langgraph.json                   # LangSmith 6 图部署配置
├── docker-compose.yml               # 完整本地栈
└── pyproject.toml                   # Python 依赖
```

---

## Agent 系统设计

### 对话处理流程

```
用户消息
  → 安全过滤（注入检测、违禁词）
  → 意图分类（是否需要身份核验？）
  ├── 通用咨询 → Supervisor → Docs Agent（RAG）
  └── 账户/订单 → HITL 邮件核验 → 注入 customer_id
                           → Supervisor → SQL/DB Agent
```

### 身份核验（HITL）

使用 LangGraph `interrupt()` 原语实现，在需要查询订单等敏感信息时自动暂停，等待用户提供邮箱后验证身份，再注入 `customer_id` 继续执行。

### 状态共享

```python
class IntermediateState(MessagesState):
    customer_id: str  # 在父图与子图间共享
```

---

## 安全特性

`backend/security/prompt_guard.py` 提供两层防护：

- **提示词注入检测**：识别 "ignore previous instructions" 等模式
- **违禁词过滤**：阻断包含预定义敏感词的请求

对应 Prometheus 指标：
- `techhub_prompt_injection_blocks_total`
- `techhub_forbidden_word_blocks_total`

---

## 监控指标

Grafana 看板（http://localhost:3001）展示：

- 请求量 / 响应时间（P50、P95、P99）
- Agent 调用成功率
- 提示词注入拦截次数
- 会话并发数

原始指标通过 `/metrics` 端点暴露给 Prometheus。

---

## 自动化模拟系统

用于生成 Demo 数据和压测，包含 10 个真实客户 Persona：

```bash
# 运行默认 7 轮对话
uv run python simulations/run_simulation.py

# 指定对话数量
uv run python simulations/run_simulation.py --count 15

# 指定特定场景（如负面情绪客户）
uv run python simulations/run_simulation.py --scenario angry_delayed_order
```

Persona 分布：6 中性 / 2 正面 / 2 负面，其中 80% 需要邮件身份核验。详见 [simulations/README.md](simulations/README.md)。

---

## Workshop 学习路径

本项目同时包含完整的 Jupyter 教学内容：

| 模块 | 主题 | 内容 |
|------|------|------|
| Module 1 | Agent 开发 | 工具调用 → 多 Agent → HITL 中断 |
| Module 2 | 评估与改进 | 离线评估、LLM-as-judge、评估驱动迭代 |
| Module 3 | 生产部署 | LangSmith 部署、在线评估、数据飞轮 |

从 `workshop_modules/module_1/section_1_foundation.ipynb` 开始。

---

## 数据集

TechHub 合成电商数据集（已内置，无需下载）：

- **50 客户**：Consumer / Corporate / Home Office 三类
- **25 商品**：笔记本 / 显示器 / 键盘 / 音频 / 配件
- **250 订单** + **439 订单项**：含真实时间分布
- **30 文档**：商品规格 + 退换货/保修/运费政策（RAG 语料）

数据库 Schema 参见 [data/structured/SCHEMA.md](data/structured/SCHEMA.md)。

---

## 环境变量参考

| 变量 | 必填 | 说明 |
|------|------|------|
| `ANTHROPIC_API_KEY` | 二选一 | Anthropic 模型 |
| `OPENAI_API_KEY` | 二选一 | OpenAI 模型 |
| `LANGSMITH_API_KEY` | 是 | LangSmith 追踪与部署 |
| `WORKSHOP_MODEL` | 否 | 默认 `anthropic:claude-haiku-4-5` |
| `EMBEDDING_PROVIDER` | 否 | `huggingface`（默认）或 `openai` |
| `LANGSMITH_PROJECT` | 否 | 默认 `langsmith-agent-lifecycle-workshop` |
| `POSTGRES_PASSWORD` | 否 | 默认 `techhub_dev` |
| `ALLOWED_ORIGINS` | 否 | CORS 白名单，默认 `http://localhost:3000` |

---

## 生产部署

项目支持 Railway（后端）+ Vercel（前端）部署：

- `Dockerfile.railway` — 轻量级生产镜像（排除 PyTorch/HuggingFace）
- `railway.toml` — Railway 部署配置
- `langgraph.json` — 定义 6 个 LangSmith 可部署图

### Railway 必填环境变量

| 变量 | 值 | 说明 |
|------|----|------|
| `OPENAI_API_KEY` | `sk-...` | OpenAI API Key |
| `WORKSHOP_MODEL` | `openai:gpt-4o-mini` | 模型选择 |
| `EMBEDDING_PROVIDER` | `openai` | 向量化提供商 |
| `REDIS_URL` | `redis://:password@host:port` | 从 Redis 服务 Variables 复制 |
| `LANGSMITH_TRACING` | `false` | 生产环境可关闭 |

> ⚠️ **不要设置 `OPENAI_BASE_URL`**，该变量必须完全删除（不是清空）。

### 部署监控（Prometheus + Grafana）

在 Railway 项目中额外添加两个服务：

**Prometheus 服务**
1. Railway → New Service → GitHub Repo → 选择本仓库
2. Settings → Build → Dockerfile Path 填写 `Dockerfile.prometheus`
3. Variables 添加：
   ```
   RAILWAY_API_HOST=aiagent-production.up.railway.app
   ```
4. Settings → Networking → 暴露端口 `9090`，记下生成的域名（如 `prometheus-production.up.railway.app`）

**Grafana 服务**
1. Railway → New Service → GitHub Repo → 选择本仓库
2. Settings → Build → Dockerfile Path 填写 `Dockerfile.grafana`
3. Variables 添加：
   ```
   GF_SECURITY_ADMIN_PASSWORD=your_password
   GF_DATASOURCE_PROMETHEUS_URL=http://prometheus.railway.internal:9090
   ```
4. Settings → Networking → 暴露端口 `3000`，获取公开域名
5. 用该域名更新前端的 `NEXT_PUBLIC_GRAFANA_URL` 环境变量（Vercel）

访问 Grafana 域名，账号 `admin` / 你设置的密码，即可查看实时监控看板。

---

## 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE) 文件。

合成数据集可自由使用和分发。
