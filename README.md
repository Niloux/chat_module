# DeepSeek API 交互模块

这是一个基于SQLite的Python模块，用于与DeepSeek API进行交互。该模块支持用户管理、对话管理、消息管理，以及多轮对话功能。

## 功能特点

- 用户管理
  - 用户注册和认证
  - API密钥管理（支持环境变量和数据库存储）
  - 用户会话管理

- 对话管理
  - 创建新对话
  - 获取对话历史
  - 删除对话
  - 支持多轮对话

- 消息管理
  - 发送和接收消息
  - 保存对话历史
  - 支持系统消息、用户消息和助手回复

- 模型支持
  - 支持普通对话模型（deepseek-chat）
  - 支持推理模型（deepseek-reasoner）
  - 支持在对话中切换模型

- Prompt模板管理
  - 创建自定义prompt模板
  - 管理多个prompt模板
  - 在对话中使用指定的prompt模板
  - 支持动态更新系统提示词

- 数据持久化
  - 使用SQLite数据库存储所有数据
  - 支持用户信息、对话历史和prompt模板的持久化

## 系统要求

- Python 3.7+
- SQLite3
- openai 库

## 安装

1. 克隆仓库：
```bash
git clone <repository_url>
cd chatAI
```

2. 安装依赖：
```bash
pip install openai
```

## 使用方法

### 基本使用

```python
from deepseek_chat import DeepSeekChat

# 初始化模块
deepseek = DeepSeekChat()

# 注册用户（需要提供有效的API密钥）
user_id = deepseek.register_user("username", "your_api_key")

# 创建对话
conversation_id = deepseek.create_conversation(
    user_id, 
    "对话标题", 
    "deepseek-chat",
    "你是一个有用的助手，请用中文回答问题。"
)

# 发送消息
response = deepseek.send_message(user_id, conversation_id, "你好！")
print(response["content"])

# 关闭连接
deepseek.close()
```

### 命令行界面（CLI）

运行示例程序：
```bash
python demo.py --username your_username
```

可用命令：
- `/help` - 显示帮助信息
- `/quit` - 退出程序
- `/model` - 切换模型（deepseek-chat/deepseek-reasoner）
- `/prompt` - 设置当前对话的系统提示词
- `/newprompt` - 创建新的prompt模板
- `/prompts` - 显示所有可用的prompt模板
- `/useprompt` - 使用指定prompt模板
- `/history` - 显示当前对话历史
- `/clear` - 清屏
- `/new` - 开始新对话

### API密钥管理

API密钥可以通过以下方式提供：
1. 环境变量：设置`DEEPSEEK_API_KEY`环境变量
2. 数据库存储：首次运行时输入API密钥，之后会自动从数据库获取
3. 命令行参数：通过`--api-key`参数提供

## 数据库结构

### 用户表（users）
- user_id: 用户ID（主键）
- username: 用户名（唯一）
- api_key: API密钥
- created_at: 创建时间

### 对话表（conversations）
- conversation_id: 对话ID（主键）
- user_id: 用户ID（外键）
- title: 对话标题
- model: 使用的模型
- created_at: 创建时间

### 消息表（messages）
- message_id: 消息ID（主键）
- conversation_id: 对话ID（外键）
- role: 消息角色（system/user/assistant）
- content: 消息内容
- reasoning_content: 推理内容（仅用于推理模型）
- created_at: 创建时间

### Prompt模板表（prompt_templates）
- template_id: 模板ID（主键）
- user_id: 用户ID（外键）
- name: 模板名称
- content: 模板内容
- created_at: 创建时间

## 注意事项

1. API密钥安全
   - 请妥善保管您的API密钥
   - 建议使用环境变量或数据库存储，避免在代码中硬编码
   - 定期更新API密钥以提高安全性

2. 数据库安全
   - 数据库文件包含敏感信息，请确保适当的访问权限
   - 建议定期备份数据库文件
   - 不要将数据库文件提交到版本控制系统

3. 使用限制
   - 注意API的调用频率限制
   - 合理使用token，避免不必要的API调用
   - 及时关闭数据库连接

## 许可证

MIT License

## 作者

[Niloux3d] 