# MiniGoogle Backend 🚀

一个功能完整的"小谷歌生态"后端平台，基于 **FastAPI + SQLAlchemy 2.0 异步 + WebSocket**。

## 功能模块

| 模块 | 功能 |
|------|------|
| 认证 | 注册 / 登录（JWT）、bcrypt 密码加密 |
| 用户 | 个人资料、头像、设置（主题/语言/偏好） |
| 好友 | 发送请求、接受/拒绝、好友列表、删除好友 |
| 聊天 | REST 历史消息 + WebSocket 实时聊天 + 离线消息 |
| 游戏 | 提交积分、个人记录、游戏排行榜 |
| 充值 | 钱包余额、创建订单、模拟回调（乐观锁防并发） |

## 项目结构

```
mini_google/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # Pydantic Settings 配置
│   ├── database.py          # 异步 SQLAlchemy 引擎
│   ├── dependencies.py      # get_db / get_current_user
│   ├── models/              # ORM 模型（7 张表）
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── routers/             # API 路由层（仅参数校验）
│   ├── services/            # 业务逻辑层
│   ├── websocket/           # WebSocket 聊天处理
│   └── utils/               # JWT、bcrypt、统一响应
├── alembic/                 # 数据库迁移
├── seed.py                  # 测试数据
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目后进入目录
cd mini_google

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 根据需要修改 .env 中的配置：
#   DATABASE_URL  （默认 SQLite，开箱即用）
#   JWT_SECRET    （生产环境务必更换）
```

### 3. 数据库初始化

**方式 A：自动建表（推荐开发用）**

应用启动时会自动调用 `create_all` 创建所有表，无需额外操作。

**方式 B：使用 Alembic 迁移（推荐生产用）**

```bash
alembic upgrade head
```

### 4. 创建测试数据（可选）

```bash
python seed.py
# 输出：
#   ✅ Created user: Alice (id=1)
#   ✅ Created user: Bob (id=2)
#   ✅ Friend relationship: Alice <-> Bob
#   ✅ Created 5 chat messages
#   ✅ Created 5 game scores
#   🎉 Seed completed successfully!
#
# 测试账号：
#   alice@example.com / alice123
#   bob@example.com   / bob12345
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc

---

## 切换 PostgreSQL（生产环境）

修改 `.env`：

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mini_google
```

安装 asyncpg（requirements.txt 已包含）：

```bash
pip install asyncpg
```

---

## 统一响应格式

所有接口返回：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

`code == 0` 表示成功，其他值为业务错误码（见 `app/utils/response.py`）。

---

## API 测试命令

> 以下示例假设服务运行在 `localhost:8000`，先运行 `python seed.py`。

### 注册与登录

```bash
# 注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"TestUser","password":"test1234"}'

# 登录（保存 token）
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"alice123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token']['access_token'])")

echo "Token: $TOKEN"
```

### 个人信息与设置

```bash
# 获取个人信息
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN"

# 更新资料
curl -X PUT http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"NewName","avatar_url":"https://example.com/avatar.jpg"}'

# 更新设置（支持部分更新）
curl -X PUT http://localhost:8000/api/users/me/settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"theme":"dark","language":"zh","notification_settings":{"email":true,"push":false}}'

# 修改密码
curl -X PUT http://localhost:8000/api/users/me/password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"old_password":"alice123","new_password":"newpassword"}'
```

### 好友系统

```bash
# Bob 登录获取 token
BOB_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"bob@example.com","password":"bob12345"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token']['access_token'])")

# Alice 发送好友请求给某用户（通过 friend_id 或 email）
curl -X POST http://localhost:8000/api/friends/request \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"bob@example.com"}'

# 查看收到的待处理申请（用 Bob 的 token）
curl http://localhost:8000/api/friends/pending \
  -H "Authorization: Bearer $BOB_TOKEN"

# Bob 接受请求（将上一步返回的 request id 替换 {id}）
curl -X PUT http://localhost:8000/api/friends/request/{id} \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"accept"}'

# 获取好友列表
curl http://localhost:8000/api/friends \
  -H "Authorization: Bearer $TOKEN"

# 删除好友（{friend_id} 为对方用户 ID）
curl -X DELETE http://localhost:8000/api/friends/{friend_id} \
  -H "Authorization: Bearer $TOKEN"
```

### 聊天（REST）

```bash
# 获取与 Bob（id=2）的历史消息（分页）
curl "http://localhost:8000/api/chat/messages/2?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

# 查询未读消息总数
curl http://localhost:8000/api/chat/unread/count \
  -H "Authorization: Bearer $TOKEN"

# 标记与某用户的消息为已读
curl -X PUT http://localhost:8000/api/chat/messages/read/2 \
  -H "Authorization: Bearer $TOKEN"
```

### 游戏积分

```bash
# 提交游戏得分
curl -X POST http://localhost:8000/api/games/score \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"game_name":"snake","score":4200,"extra_data":{"level":10,"duration_seconds":300}}'

# 查询个人记录（可按 game_name 过滤）
curl "http://localhost:8000/api/games/scores?game_name=snake" \
  -H "Authorization: Bearer $TOKEN"

# 排行榜（snake 游戏前 10 名）
curl "http://localhost:8000/api/games/leaderboard/snake?top_n=10" \
  -H "Authorization: Bearer $TOKEN"
```

### 充值流程

```bash
# 查询钱包余额
curl http://localhost:8000/api/wallet/balance \
  -H "Authorization: Bearer $TOKEN"

# 创建充值订单（amount 单位：分，5000 = 50 元）
ORDER_NO=$(curl -s -X POST http://localhost:8000/api/recharge/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":5000,"payment_method":"alipay"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['order_no'])")

echo "Order: $ORDER_NO"

# ⚠️  模拟支付回调（生产环境由支付平台调用，需验证签名）
curl -X POST http://localhost:8000/api/recharge/callback \
  -H "Content-Type: application/json" \
  -d "{\"order_no\":\"$ORDER_NO\"}"

# 再次查询余额（应增加 5000 分 = 50 元）
curl http://localhost:8000/api/wallet/balance \
  -H "Authorization: Bearer $TOKEN"

# 查看充值历史
curl http://localhost:8000/api/recharge/orders \
  -H "Authorization: Bearer $TOKEN"
```

---

## WebSocket 实时聊天

### 连接地址

```
ws://localhost:8000/ws/chat?token=<your_jwt_token>
```

Token 通过登录接口获取，连接时通过 query 参数传递。

### 消息协议

所有消息均为 JSON 格式。

**客户端发送消息：**

```json
{"type": "chat", "to_user_id": 2, "message": "Hello Bob!"}
```

**服务器推送消息（实时/离线）：**

```json
{
  "type": "message",
  "from_user_id": 1,
  "message": "Hello Bob!",
  "message_id": 42,
  "created_at": "2024-01-01T12:00:00"
}
```

**发送确认（发送方收到）：**

```json
{"type": "sent", "message_id": 42, "to_user_id": 2, "delivered": true}
```

**标记已读（客户端发送）：**

```json
{"type": "read", "from_user_id": 1}
```

**已读回执（服务器推给发送方）：**

```json
{"type": "read_receipt", "by_user_id": 2, "count": 3}
```

**心跳：**

```json
// 发送
{"type": "ping"}
// 响应
{"type": "pong"}
```

### 测试方法

**方法 1：使用 websocat（推荐）**

```bash
# 安装 websocat
# macOS: brew install websocat
# Linux: cargo install websocat

# 获取 Alice 的 token
ALICE_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"alice123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token']['access_token'])")

# 连接 WebSocket（Alice）
websocat "ws://localhost:8000/ws/chat?token=$ALICE_TOKEN"

# 在终端中输入并发送：
{"type":"chat","to_user_id":2,"message":"Hello Bob!"}
{"type":"ping"}
```

**方法 2：浏览器控制台**

在浏览器控制台执行：

```javascript
// 替换为实际 token
const token = "YOUR_JWT_TOKEN_HERE";
const ws = new WebSocket(`ws://localhost:8000/ws/chat?token=${token}`);

ws.onopen = () => {
  console.log("Connected!");
  // 发送消息
  ws.send(JSON.stringify({type: "chat", to_user_id: 2, message: "Hello from browser!"}));
};

ws.onmessage = (event) => {
  console.log("Received:", JSON.parse(event.data));
};

ws.onclose = (event) => {
  console.log("Disconnected:", event.code, event.reason);
};

// 发送消息
ws.send(JSON.stringify({type: "chat", to_user_id: 2, message: "Second message"}));

// 标记已读
ws.send(JSON.stringify({type: "read", from_user_id: 2}));

// 心跳
ws.send(JSON.stringify({type: "ping"}));
```

**方法 3：Python 测试脚本**

```python
import asyncio
import websockets
import json

async def test_ws():
    token = "YOUR_JWT_TOKEN"
    uri = f"ws://localhost:8000/ws/chat?token={token}"
    
    async with websockets.connect(uri) as ws:
        print("Connected! Waiting for offline messages...")
        
        # 发送一条消息
        await ws.send(json.dumps({
            "type": "chat",
            "to_user_id": 2,
            "message": "Hello via Python!"
        }))
        
        # 接收响应（循环 3 次）
        for _ in range(3):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print("Got:", json.loads(msg))
            except asyncio.TimeoutError:
                break

asyncio.run(test_ws())
```

---

## 离线消息机制

当用户 A 给离线的用户 B 发送消息时：
1. 消息正常保存到 `chat_messages` 表，`is_read = False`
2. WebSocket 推送失败（B 不在线），消息作为离线消息留在 DB
3. 用户 B 重新连接 WebSocket 时，服务器自动推送所有未读消息

---

## 错误码速查

| 错误码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1001 | 用户不存在 |
| 1002 | 用户已存在（邮箱或用户名重复） |
| 1003 | 邮箱或密码错误 |
| 1004 | 账号已停用 |
| 1005 | 旧密码错误 |
| 2001 | 好友关系已存在 |
| 2002 | 好友请求不存在 |
| 2003 | 不能添加自己为好友 |
| 2004 | 好友关系不存在 |
| 5001 | 钱包不存在 |
| 5002 | 订单不存在 |
| 5003 | 订单已支付 |
| 9001 | 未授权（Token 无效或过期） |
| 9003 | 参数校验失败 |
| 9999 | 服务器内部错误 |

---

## 扩展指南

### 接入真实支付

1. 修改 `app/routers/recharge.py` 中 `/api/recharge/order` 接口，调用支付平台 SDK 生成支付链接
2. 替换 `/api/recharge/callback` 为支付平台异步通知路由，添加签名验证逻辑
3. `wallet_service.py` 中的乐观锁逻辑无需修改，天然支持并发安全

### 添加邮箱验证

`users` 表已预留 `email_verified` 字段，只需：
1. 注册时发送验证邮件（添加邮件发送 service）
2. 添加 `GET /api/auth/verify-email?token=xxx` 接口标记已验证

### 添加新游戏

直接调用 `POST /api/games/score` 传入新的 `game_name`，无需任何后端改动：

```json
{"game_name": "minesweeper", "score": 999, "extra_data": {"difficulty": "expert"}}
```

### 水平扩展 WebSocket

当前 `active_connections` 是进程内 dict，多进程部署时需替换为 Redis Pub/Sub：
1. 安装 `aioredis`
2. 用户上线时 `SUBSCRIBE user:{id}`，发消息时 `PUBLISH user:{to_id} payload`
3. 每个进程订阅并转发给本地连接

---

## 技术栈

- **框架**: FastAPI 0.111 + Uvicorn
- **ORM**: SQLAlchemy 2.0（异步）+ Alembic
- **数据库**: SQLite（开发） / PostgreSQL（生产）
- **认证**: JWT（python-jose）+ bcrypt
- **实时通信**: WebSocket（原生 FastAPI）
- **配置**: Pydantic Settings（.env）
- **Python**: 3.10+
