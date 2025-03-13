#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DeepSeek API交互模块使用示例脚本

此脚本演示了如何使用DeepSeek API交互模块进行对话。
用户可以通过命令行与DeepSeek模型进行交互，支持普通对话模型和推理模型。
"""

import argparse
import os

from deepseek_chat import DeepSeekChat


def clear_screen():
    """清屏"""
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    """打印应用标题"""
    banner = """
    ====================================
    |                                  |
    |   DeepSeek 聊天 CLI 示例程序     |
    |                                  |
    ====================================
    """
    print(banner)


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


def get_api_key(deepseek: DeepSeekChat, username: str) -> str:
    """获取API密钥"""
    # 先尝试从环境变量获取
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if api_key:
        return api_key

    # 尝试从数据库获取
    user = deepseek.user_manager.get_user(username)
    if user and user["api_key"]:
        return user["api_key"]

    # 如果都没有，则请求用户输入
    api_key = input("请输入DeepSeek API密钥: ")
    return api_key


def main():  # noqa: C901
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="DeepSeek API交互示例")
    parser.add_argument("--db", default="deepseek.db", help="数据库文件路径")
    parser.add_argument(
        "--model",
        default="deepseek-chat",
        choices=["deepseek-chat", "deepseek-reasoner"],
        help="使用的模型",
    )
    parser.add_argument("--username", default="default_user", help="用户名")
    args = parser.parse_args()

    clear_screen()
    print_banner()

    # 初始化模块
    deepseek = DeepSeekChat(args.db)
    api_key = get_api_key(deepseek, args.username)

    try:
        # 注册用户或更新API密钥
        user = deepseek.user_manager.get_user(args.username)
        if user:
            # 如果用户存在但API密钥不同，更新API密钥
            if user["api_key"] != api_key:
                deepseek.user_manager.update_user_api_key(user["user_id"], api_key)
            user_id = user["user_id"]
        else:
            # 创建新用户
            user_id = deepseek.register_user(args.username, api_key)

        # 创建对话
        print("正在创建新对话...")
        conversation_id = deepseek.create_conversation(
            user_id, "CLI对话", args.model, "你是一个有用的助手，请用中文回答问题。"
        )

        # 当前使用的模型
        current_model = args.model

        print_help()
        print(f"当前模型: {current_model}")
        print("输入 /help 查看可用命令")
        print("开始对话...\n")

        while True:
            # 获取用户输入
            user_input = input("User: ")

            # 处理命令
            if user_input.startswith("/"):
                cmd = user_input.lower()

                if cmd == "/quit":
                    print("再见！")
                    break
                elif cmd == "/help":
                    print_help()
                    continue
                elif cmd == "/model":
                    if current_model == "deepseek-chat":
                        current_model = "deepseek-reasoner"
                    else:
                        current_model = "deepseek-chat"

                    deepseek.update_conversation_model(conversation_id, current_model)
                    print(f"已切换到模型: {current_model}")
                    continue
                elif cmd == "/prompts":
                    # 显示所有prompt模板
                    prompts = deepseek.get_user_prompts(user_id)
                    if prompts:
                        print("\n可用的prompt模板:")
                        for prompt in prompts:
                            print(
                                f"ID: {prompt['template_id']}, 名称: {prompt['name']}"
                            )
                            print(f"内容: {prompt['content']}")
                            print("-" * 40)
                    else:
                        print("没有可用的prompt模板，使用 /newprompt 创建")
                    continue
                elif cmd.startswith("/prompt"):
                    # 设置系统提示词
                    if len(user_input) > 8:  # "/prompt "的长度是8
                        new_prompt = user_input[8:]
                        # 修改对话中的系统消息
                        try:
                            # 获取当前对话的所有消息
                            messages = deepseek.get_conversation_history(
                                conversation_id
                            )
                            # 找到系统消息
                            system_msg_found = False
                            for msg in messages:
                                if msg["role"] == "system":
                                    # 更新系统消息
                                    deepseek.message_manager.add_message(
                                        conversation_id, "system", new_prompt, None
                                    )
                                    system_msg_found = True
                                    print(f"已设置系统提示词: {new_prompt}")
                                    break

                            if not system_msg_found:
                                # 如果没有找到系统消息，创建一个
                                deepseek.message_manager.add_message(
                                    conversation_id, "system", new_prompt
                                )
                                print(f"已设置系统提示词: {new_prompt}")
                        except Exception as e:
                            print(f"设置系统提示词失败: {e}")
                    else:
                        print("请指定系统提示词，例如: /prompt 你是一个有用的助手")
                    continue
                elif cmd.startswith("/newprompt"):
                    # 创建新的prompt模板
                    parts = user_input[10:].strip().split(" ", 1)
                    if len(parts) == 2:
                        name, content = parts
                        template_id = deepseek.create_prompt(user_id, name, content)
                        print(f"已创建prompt模板 (ID: {template_id}): {name}")
                    else:
                        print("格式错误，正确格式: /newprompt 名称 内容")
                    continue
                elif cmd.startswith("/useprompt"):
                    # 使用指定的prompt模板
                    try:
                        prompt_id = int(user_input[10:].strip())
                        prompt = deepseek.prompt_manager.get_prompt(prompt_id)
                        if prompt:
                            # 先删除现有的系统消息
                            messages = deepseek.get_conversation_history(
                                conversation_id
                            )
                            system_msg_found = False
                            for msg in messages:
                                if msg["role"] == "system":
                                    system_msg_found = True
                                    break

                            if system_msg_found:
                                # 更新系统消息
                                try:
                                    # 使用新的系统消息
                                    deepseek.message_manager.add_message(
                                        conversation_id, "system", prompt["content"]
                                    )
                                    print(f"已使用prompt模板: {prompt['name']}")
                                except Exception as e:
                                    print(f"应用prompt模板失败: {e}")
                            else:
                                # 添加系统消息
                                deepseek.message_manager.add_message(
                                    conversation_id, "system", prompt["content"]
                                )
                                print(f"已使用prompt模板: {prompt['name']}")
                        else:
                            print(f"找不到ID为 {prompt_id} 的prompt模板")
                    except ValueError:
                        print("请指定有效的prompt模板ID，例如: /useprompt 1")
                    continue
                elif cmd == "/history":
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
                    print()
                    continue
                elif cmd == "/clear":
                    clear_screen()
                    print_banner()
                    print(f"当前模型: {current_model}")
                    continue
                elif cmd == "/new":
                    # 开始新对话时，可以选择是否使用已有的prompt模板
                    prompts = deepseek.get_user_prompts(user_id)
                    if prompts:
                        print("\n可用的prompt模板:")
                        for prompt in prompts:
                            print(
                                f"ID: {prompt['template_id']}, 名称: {prompt['name']}"
                            )

                        print("\n请选择要使用的prompt模板ID，或直接回车使用默认提示词")
                        prompt_id_input = input("Prompt ID: ").strip()

                        if prompt_id_input:
                            try:
                                prompt_id = int(prompt_id_input)
                                # 使用指定的prompt模板创建对话
                                try:
                                    conversation_id = (
                                        deepseek.create_conversation_with_prompt(
                                            user_id, "CLI对话", current_model, prompt_id
                                        )
                                    )
                                    print("已创建新对话，使用指定的prompt模板")
                                except ValueError as e:
                                    print(f"创建对话失败: {e}")
                                    # 使用默认提示词创建对话
                                    conversation_id = deepseek.create_conversation(
                                        user_id,
                                        "CLI对话",
                                        current_model,
                                        "你是一个有用的助手，请用中文回答问题。",
                                    )
                                    print("已创建新对话，使用默认提示词")
                            except ValueError:
                                print("无效的prompt ID，使用默认提示词")
                                conversation_id = deepseek.create_conversation(
                                    user_id,
                                    "CLI对话",
                                    current_model,
                                    "你是一个有用的助手，请用中文回答问题。",
                                )
                                print("已创建新对话")
                        else:
                            # 使用默认提示词创建对话
                            conversation_id = deepseek.create_conversation(
                                user_id,
                                "CLI对话",
                                current_model,
                                "你是一个有用的助手，请用中文回答问题。",
                            )
                            print("已创建新对话")
                    else:
                        # 没有可用的prompt模板，使用默认提示词
                        conversation_id = deepseek.create_conversation(
                            user_id,
                            "CLI对话",
                            current_model,
                            "你是一个有用的助手，请用中文回答问题。",
                        )
                        print("已创建新对话")
                    continue

            # 发送消息并获取回复
            try:
                response = deepseek.send_message(user_id, conversation_id, user_input)

                if "reasoning_content" in response and response["reasoning_content"]:
                    print(f"\nAI (推理过程):\n{response['reasoning_content']}\n")

                print(f"AI: {response['content']}")
            except Exception as e:
                print(f"错误: {e}")

    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # 关闭连接
        deepseek.close()
        print("已关闭数据库连接")


if __name__ == "__main__":
    main()
