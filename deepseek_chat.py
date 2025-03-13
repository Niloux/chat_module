#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DeepSeek API 交互模块

此模块提供了与DeepSeek API交互的功能，使用SQLite数据库存储用户信息和对话历史。
支持功能：
1. 用户管理（创建、获取用户信息）
2. 对话管理（创建、获取、删除对话）
3. 消息管理（创建、获取消息历史）
4. 与DeepSeek API交互（单轮对话、多轮对话，支持普通对话模型和推理模型）
"""

import os
import sqlite3
from typing import Dict, List, Optional

from openai import OpenAI


class DeepSeekDB:
    """数据库管理类，负责创建和维护SQLite数据库及其表结构"""

    def __init__(self, db_path: str = "deepseek.db"):
        """
        初始化数据库连接并创建必要的表

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """创建数据库所需的表"""

        # 用户表
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            api_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 对话表
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        """)

        # 消息表
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            reasoning_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
        )
        """)

        # Prompt模板表
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_templates (
            template_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE (user_id, name)
        )
        """)

        self.conn.commit()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


class UserManager:
    """用户管理类"""

    def __init__(self, db):
        self.db = db

    def create_user(self, username: str, api_key: str) -> int:
        """创建新用户"""
        self.db.cursor.execute(
            "INSERT INTO users (username, api_key) VALUES (?, ?)",
            (username, api_key),
        )
        self.db.conn.commit()
        return self.db.cursor.lastrowid

    def get_user(self, username: str) -> Optional[Dict]:
        """获取用户信息"""
        self.db.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.db.cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "api_key": row[2],
                "created_at": row[3],
            }
        return None

    def get_user_api_key(self, user_id: int) -> Optional[str]:
        """获取用户的API密钥"""
        self.db.cursor.execute(
            "SELECT api_key FROM users WHERE user_id = ?", (user_id,)
        )
        row = self.db.cursor.fetchone()
        return row[0] if row else None

    def update_user_api_key(self, user_id: int, api_key: str) -> None:
        """更新用户的API密钥"""
        self.db.cursor.execute(
            "UPDATE users SET api_key = ? WHERE user_id = ?", (api_key, user_id)
        )
        self.db.conn.commit()


class ConversationManager:
    """对话管理类，处理对话相关操作"""

    def __init__(self, db: DeepSeekDB):
        """
        初始化对话管理器

        Args:
            db: 数据库管理对象
        """
        self.db = db

    def create_conversation(
        self, user_id: int, title: str, model: str = "deepseek-chat"
    ) -> int:
        """
        创建新对话

        Args:
            user_id: 用户ID
            title: 对话标题
            model: 使用的模型，默认为deepseek-chat

        Returns:
            新创建对话的ID
        """
        self.db.cursor.execute(
            "INSERT INTO conversations (user_id, title, model) VALUES (?, ?, ?)",
            (user_id, title, model),
        )
        self.db.conn.commit()
        return self.db.cursor.lastrowid

    def get_conversation(self, conversation_id: int) -> Dict:
        """
        获取对话信息

        Args:
            conversation_id: 对话ID

        Returns:
            对话信息字典
        """
        self.db.cursor.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,)
        )
        conv = self.db.cursor.fetchone()
        if conv:
            return dict(conv)
        return None

    def get_user_conversations(self, user_id: int) -> List[Dict]:
        """
        获取用户的所有对话

        Args:
            user_id: 用户ID

        Returns:
            对话信息字典列表
        """
        self.db.cursor.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        conversations = self.db.cursor.fetchall()
        return [dict(conv) for conv in conversations]

    def update_conversation_model(self, conversation_id: int, model: str) -> bool:
        """
        更新对话使用的模型

        Args:
            conversation_id: 对话ID
            model: 新的模型名称

        Returns:
            更新是否成功
        """
        self.db.cursor.execute(
            "UPDATE conversations SET model = ? WHERE conversation_id = ?",
            (model, conversation_id),
        )
        self.db.conn.commit()
        return self.db.cursor.rowcount > 0

    def delete_conversation(self, conversation_id: int) -> bool:
        """
        删除对话及其相关消息

        Args:
            conversation_id: 对话ID

        Returns:
            删除是否成功
        """
        # 先删除对话中的所有消息
        self.db.cursor.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
        )
        # 再删除对话本身
        self.db.cursor.execute(
            "DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,)
        )
        self.db.conn.commit()
        return self.db.cursor.rowcount > 0


class MessageManager:
    """消息管理类，处理消息相关操作"""

    def __init__(self, db: DeepSeekDB):
        """
        初始化消息管理器

        Args:
            db: 数据库管理对象
        """
        self.db = db

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        reasoning_content: str = None,
    ) -> int:
        """
        添加新消息

        Args:
            conversation_id: 对话ID
            role: 消息角色（user/assistant/system）
            content: 消息内容
            reasoning_content: 推理内容（仅对assistant消息且使用推理模型时有效）

        Returns:
            新创建消息的ID
        """
        self.db.cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, reasoning_content) VALUES (?, ?, ?, ?)",  # noqa: E501
            (conversation_id, role, content, reasoning_content),
        )
        self.db.conn.commit()
        return self.db.cursor.lastrowid

    def get_conversation_messages(self, conversation_id: int) -> List[Dict]:
        """
        获取对话的所有消息

        Args:
            conversation_id: 对话ID

        Returns:
            消息信息字典列表
        """
        self.db.cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )
        messages = self.db.cursor.fetchall()
        return [dict(msg) for msg in messages]

    def get_formatted_messages(self, conversation_id: int) -> List[Dict]:
        """
        获取格式化后的消息列表，用于API调用

        Args:
            conversation_id: 对话ID

        Returns:
            格式化后的消息列表
        """
        self.db.cursor.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",  # noqa: E501
            (conversation_id,),
        )
        messages = self.db.cursor.fetchall()
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]


class DeepSeekAPI:
    """DeepSeek API交互类，处理与API的通信"""

    def __init__(self, api_key: str):
        """
        初始化API客户端

        Args:
            api_key: DeepSeek API密钥
        """
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    def chat_completion(
        self, messages: List[Dict], model: str = "deepseek-chat", **kwargs
    ) -> Dict:
        """
        非流式聊天完成请求

        Args:
            messages: 消息列表
            model: 使用的模型
            **kwargs: 其他参数

        Returns:
            API响应
        """
        response = self.client.chat.completions.create(
            model=model, messages=messages, stream=False, **kwargs
        )
        return response

    def is_reasoner_model(self, model: str) -> bool:
        """
        判断是否为推理模型

        Args:
            model: 模型名称

        Returns:
            是否为推理模型
        """
        return model == "deepseek-reasoner"


class PromptManager:
    """Prompt模板管理类，处理用户prompt模板相关操作"""

    def __init__(self, db: DeepSeekDB):
        """
        初始化Prompt管理器

        Args:
            db: 数据库管理对象
        """
        self.db = db

    def create_prompt(self, user_id: int, name: str, content: str) -> int:
        """
        创建新的prompt模板

        Args:
            user_id: 用户ID
            name: 模板名称
            content: 模板内容

        Returns:
            新创建模板的ID
        """
        try:
            self.db.cursor.execute(
                "INSERT INTO prompt_templates (user_id, name, content) VALUES (?, ?, ?)",
                (user_id, name, content),
            )
            self.db.conn.commit()
            return self.db.cursor.lastrowid
        except sqlite3.IntegrityError:
            # 模板名称已存在，更新内容
            self.db.cursor.execute(
                "UPDATE prompt_templates SET content = ? WHERE user_id = ? AND name = ?",
                (content, user_id, name),
            )
            self.db.conn.commit()

            # 获取更新的模板ID
            self.db.cursor.execute(
                "SELECT template_id FROM prompt_templates WHERE user_id = ? AND name = ?",
                (user_id, name),
            )
            return self.db.cursor.fetchone()["template_id"]

    def get_prompt(self, template_id: int) -> Dict:
        """
        获取prompt模板信息

        Args:
            template_id: 模板ID

        Returns:
            模板信息字典
        """
        self.db.cursor.execute(
            "SELECT * FROM prompt_templates WHERE template_id = ?", (template_id,)
        )
        template = self.db.cursor.fetchone()
        if template:
            return dict(template)
        return None

    def get_user_prompts(self, user_id: int) -> List[Dict]:
        """
        获取用户的所有prompt模板

        Args:
            user_id: 用户ID

        Returns:
            模板信息字典列表
        """
        self.db.cursor.execute(
            "SELECT * FROM prompt_templates WHERE user_id = ? ORDER BY name ASC",
            (user_id,),
        )
        templates = self.db.cursor.fetchall()
        return [dict(template) for template in templates]

    def delete_prompt(self, template_id: int) -> bool:
        """
        删除prompt模板

        Args:
            template_id: 模板ID

        Returns:
            删除是否成功
        """
        self.db.cursor.execute(
            "DELETE FROM prompt_templates WHERE template_id = ?", (template_id,)
        )
        self.db.conn.commit()
        return self.db.cursor.rowcount > 0


class DeepSeekChat:
    """DeepSeek聊天类，封装了所有操作"""

    def __init__(self, db_path: str = "deepseek.db"):
        """
        初始化DeepSeekChat

        Args:
            db_path: 数据库文件路径
        """
        self.db = DeepSeekDB(db_path)
        self.user_manager = UserManager(self.db)
        self.conversation_manager = ConversationManager(self.db)
        self.message_manager = MessageManager(self.db)
        self.prompt_manager = PromptManager(self.db)
        self.api_clients = {}  # 用户ID到API客户端的映射

    def register_user(self, username: str, api_key: str) -> int:
        """
        注册新用户

        Args:
            username: 用户名
            api_key: DeepSeek API密钥

        Returns:
            用户ID
        """
        user_id = self.user_manager.create_user(username, api_key)
        # 创建API客户端
        self.api_clients[user_id] = DeepSeekAPI(api_key)
        return user_id

    def get_api_client(self, user_id: int) -> DeepSeekAPI:
        """
        获取用户的API客户端

        Args:
            user_id: 用户ID

        Returns:
            API客户端对象
        """
        if user_id not in self.api_clients:
            user = self.user_manager.get_user(user_id)
            if user:
                self.api_clients[user_id] = DeepSeekAPI(user["api_key"])
        return self.api_clients.get(user_id)

    def create_conversation(
        self,
        user_id: int,
        title: str,
        model: str = "deepseek-chat",
        system_prompt: str = "You are a helpful assistant.",
    ) -> int:
        """
        创建新对话

        Args:
            user_id: 用户ID
            title: 对话标题
            model: 使用的模型
            system_prompt: 系统提示

        Returns:
            对话ID
        """
        conv_id = self.conversation_manager.create_conversation(user_id, title, model)
        # 添加系统消息
        self.message_manager.add_message(conv_id, "system", system_prompt)
        return conv_id

    def send_message(
        self, user_id: int, conversation_id: int, content: str, **kwargs
    ) -> Dict:
        """
        发送消息并获取回复

        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            content: 用户消息内容
            **kwargs: 其他参数

        Returns:
            回复信息字典
        """
        # 获取对话信息
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"对话不存在: {conversation_id}")

        # 添加用户消息
        self.message_manager.add_message(conversation_id, "user", content)

        # 获取格式化的消息列表
        messages = self.message_manager.get_formatted_messages(conversation_id)

        # 获取API客户端
        api_client = self.get_api_client(user_id)
        if not api_client:
            raise ValueError(f"用户不存在或API密钥无效: {user_id}")

        # 调用API获取回复
        response = api_client.chat_completion(
            messages, model=conversation["model"], **kwargs
        )

        # 处理回复
        if api_client.is_reasoner_model(conversation["model"]):
            # 推理模型回复包含reasoning_content
            reasoning_content = response.choices[0].message.reasoning_content
            content = response.choices[0].message.content

            # 添加助手回复到数据库
            self.message_manager.add_message(
                conversation_id, "assistant", content, reasoning_content
            )

            return {"content": content, "reasoning_content": reasoning_content}
        else:
            # 普通模型回复
            content = response.choices[0].message.content

            # 添加助手回复到数据库
            self.message_manager.add_message(conversation_id, "assistant", content)

            return {"content": content}

    def get_conversation_history(self, conversation_id: int) -> List[Dict]:
        """
        获取对话历史

        Args:
            conversation_id: 对话ID

        Returns:
            消息信息字典列表
        """
        return self.message_manager.get_conversation_messages(conversation_id)

    def update_conversation_model(self, conversation_id: int, model: str) -> bool:
        """
        更新对话使用的模型

        Args:
            conversation_id: 对话ID
            model: 新的模型名称

        Returns:
            更新是否成功
        """
        return self.conversation_manager.update_conversation_model(
            conversation_id, model
        )

    def delete_conversation(self, conversation_id: int) -> bool:
        """
        删除对话

        Args:
            conversation_id: 对话ID

        Returns:
            删除是否成功
        """
        return self.conversation_manager.delete_conversation(conversation_id)

    def close(self):
        """关闭数据库连接"""
        self.db.close()

    def create_prompt(self, user_id: int, name: str, content: str) -> int:
        """
        创建prompt模板

        Args:
            user_id: 用户ID
            name: 模板名称
            content: 模板内容

        Returns:
            模板ID
        """
        return self.prompt_manager.create_prompt(user_id, name, content)

    def get_user_prompts(self, user_id: int) -> List[Dict]:
        """
        获取用户的所有prompt模板

        Args:
            user_id: 用户ID

        Returns:
            模板列表
        """
        return self.prompt_manager.get_user_prompts(user_id)

    def create_conversation_with_prompt(
        self, user_id: int, title: str, model: str, prompt_id: int
    ) -> int:
        """
        使用指定prompt模板创建对话

        Args:
            user_id: 用户ID
            title: 对话标题
            model: 使用的模型
            prompt_id: 使用的prompt模板ID

        Returns:
            对话ID
        """
        # 获取prompt模板内容
        prompt = self.prompt_manager.get_prompt(prompt_id)
        if not prompt:
            raise ValueError(f"Prompt模板不存在: {prompt_id}")

        # 创建对话并设置prompt
        conv_id = self.conversation_manager.create_conversation(user_id, title, model)
        self.message_manager.add_message(conv_id, "system", prompt["content"])
        return conv_id


# 示例用法
if __name__ == "__main__":
    # 初始化DeepSeekChat
    deepseek = DeepSeekChat()

    # 注册用户（需要提供有效的API密钥）
    api_key = os.environ.get("DEEPSEEK_API_KEY", "your_api_key_here")
    user_id = deepseek.register_user("test_user", api_key)

    # 创建对话
    conversation_id = deepseek.create_conversation(
        user_id, "测试对话", "deepseek-chat", "你是一个有用的助手，请用中文回答问题。"
    )

    # 发送消息并获取回复
    try:
        response = deepseek.send_message(
            user_id, conversation_id, "你好，今天天气怎么样？"
        )
        print(f"AI: {response['content']}")

        # 再发送一条消息
        response = deepseek.send_message(user_id, conversation_id, "介绍一下你自己")
        print(f"AI: {response['content']}")

        # 切换到推理模型
        deepseek.update_conversation_model(conversation_id, "deepseek-reasoner")

        # 使用推理模型发送消息
        response = deepseek.send_message(
            user_id, conversation_id, "计算 15 + 27 等于多少？"
        )
        print(f"推理过程: {response['reasoning_content']}")
        print(f"AI: {response['content']}")

        # 获取对话历史
        history = deepseek.get_conversation_history(conversation_id)
        print("\n对话历史:")
        for msg in history:
            if msg["role"] == "system":
                print(f"System: {msg['content']}")
            elif msg["role"] == "user":
                print(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                if msg["reasoning_content"]:
                    print(f"AI (推理): {msg['reasoning_content']}")
                print(f"AI: {msg['content']}")

    except Exception as e:
        print(f"错误: {e}")

    finally:
        # 关闭连接
        deepseek.close()


def print_help():
    """打印帮助信息"""
    help_text = """
    可用命令:
    /help       - 显示此帮助信息
    /quit       - 退出程序
    /model      - 切换模型 (deepseek-chat/deepseek-reasoner)
    /prompt     - 设置当前对话的系统提示词，例如: /prompt 你是一个有用的助手
    /newprompt  - 创建新的prompt模板，例如: /newprompt 助手 你是一个有用的助手
    /prompts    - 显示所有可用的prompt模板
    /useprompt  - 使用指定prompt模板，例如: /useprompt 1
    /history    - 显示当前对话历史
    /clear      - 清屏
    /new        - 开始新对话
    """
    print(help_text)
