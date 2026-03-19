# 易策 (yice) Web 应用

基于 FastAPI + Vue 3 的易策决策系统 Web 界面。

## 功能特性

- 🤖 **LLM 配置管理** - 可视化配置多个 LLM Provider 和 Agent
- 🔗 **连通性测试** - 实时测试 API 连接状态
- 📜 **历史记录** - 查看和管理占卜决策记录
- 🔄 **实时推演** - WebSocket 实时流式展示六爻分析过程

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- npm 或 pnpm

### 安装

#### 1. 后端安装

```bash
cd web/backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 2. 前端安装

```bash
cd web/frontend

# 安装依赖
npm install
```

### 启动应用

#### 方式一：使用统一启动脚本（推荐）

```bash
# 在项目根目录执行
python web/main.py
```

这将自动：
- 启动后端服务 (默认端口 8000)
- 启动前端开发服务器 (默认端口 5173)
- 自动打开浏览器访问 http://localhost:5173

#### 方式二：分别启动

**启动后端：**

```bash
cd web/backend
source venv/bin/activate  # 激活虚拟环境
uvicorn main:app --reload --port 8000
```

**启动前端（新终端）：**

```bash
cd web/frontend
npm run dev
```

然后访问 http://localhost:5173

## 环境变量

可以通过环境变量自定义配置：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `YICE_BACKEND_PORT` | 后端服务端口 | `8000` |
| `YICE_FRONTEND_PORT` | 前端服务端口 | `5173` |
| `YICE_NO_OPEN` | 不自动打开浏览器 | `false` |

示例：

```bash
YICE_BACKEND_PORT=9000 YICE_NO_OPEN=1 python web/main.py
```

## 目录结构

```
web/
├── main.py                    # 统一启动脚本
├── backend/
│   ├── main.py                # FastAPI 应用入口
│   ├── requirements.txt       # Python 依赖
│   ├── routes/
│   │   ├── config.py          # 配置管理 API
│   │   ├── history.py         # 历史记录 API
│   │   └── websocket.py       # WebSocket 实时通信
│   └── services/
│       └── agent_bridge.py    # Agent 桥接服务
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── SettingsView.vue    # 配置页面
│   │   │   ├── HistoryView.vue     # 历史记录页面
│   │   │   └── DivinationView.vue  # 占卜页面
│   │   ├── stores/                 # Pinia 状态管理
│   │   └── services/               # WebSocket 服务
│   └── package.json
└── history/                   # 历史记录存储目录 (运行时创建)
```

## API 文档

启动应用后访问：http://localhost:8000/docs

### 主要接口

#### 配置管理

- `GET /api/config/` - 获取当前配置
- `PUT /api/config/` - 更新配置
- `POST /api/config/test` - 测试 LLM 连接

#### 历史记录

- `GET /api/history/` - 获取历史记录列表
- `GET /api/history/{id}` - 获取单条记录详情
- `POST /api/history/` - 创建新记录
- `DELETE /api/history/{id}` - 删除记录

#### WebSocket

- `/ws/agent` - 起卦官对话
- `/ws/divination` - 完整推演流程

## 配置 LLM

首次使用需要在 **设置页面** 配置 LLM Provider：

1. 访问 http://localhost:5173/settings
2. 添加 Provider（如：minimax, openai 等）
3. 填写 API Key 和 Base URL
4. 点击 "测试连接" 验证配置
5. 为每个 Agent 分配使用的 Provider 和模型
6. 点击 "保存配置"

配置文件保存在项目根目录的 `models.json`。

### 配置示例

```json
{
  "providers": {
    "minimax": {
      "api_key": "sk-xxx",
      "base_url": "https://api.minimax.chat",
      "default_model": "MiniMax-M2.5"
    }
  },
  "agents": {
    "qigua_agent": {"provider": "minimax", "model": "MiniMax-M2.5"},
    "scene_router": {"provider": "minimax", "model": "MiniMax-M2.5"},
    "yao_agent": {"provider": "minimax", "model": "MiniMax-M2.5"},
    "reporter": {"provider": "minimax", "model": "MiniMax-M2.5"}
  }
}
```

## 开发

### 后端开发

```bash
cd web/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 前端开发

```bash
cd web/frontend
npm run dev
```

### 构建生产版本

```bash
cd web/frontend
npm run build
```

构建产物输出到 `web/frontend/dist` 目录。

## 故障排除

### 后端启动失败

1. 检查虚拟环境是否正确激活
2. 确认依赖已安装：`pip install -r requirements.txt`
3. 检查端口是否被占用：`lsof -i :8000`

### 前端启动失败

1. 检查 Node.js 版本：`node --version` (需要 18+)
2. 重新安装依赖：`rm -rf node_modules && npm install`
3. 清除缓存：`npm run dev -- --force`

### WebSocket 连接失败

1. 确认后端服务正常运行
2. 检查防火墙设置
3. 查看浏览器控制台错误信息

## 数据存储

- **配置文件**: `models.json` (项目根目录)
- **历史记录**: `web/history/*.json` (运行时自动创建)

## 技术栈

### 后端

- **FastAPI** - 现代 Python Web 框架
- **Uvicorn** - ASGI 服务器
- **urllib** - HTTP 客户端 (零依赖)

### 前端

- **Vue 3** - 渐进式 JavaScript 框架
- **Pinia** - Vue 3 状态管理
- **Vite** - 下一代前端构建工具
- **TypeScript** - 类型安全

## 许可证

MIT License

## 作者

阿木 (Amu) + 邵琦 (Shaoqi)
