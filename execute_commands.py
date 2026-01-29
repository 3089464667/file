#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 Kali Linux 上执行 conversations.json 中的命令并将输出填入对应的 gpt value 中

使用方法：
    python3 execute_commands.py [--input INPUT_FILE] [--output OUTPUT_FILE] [--timeout SECONDS] [--start INDEX] [--end INDEX]

参数说明：
    --input:   输入的 JSON 文件路径 (默认: conversations.json)
    --output:  输出的 JSON 文件路径 (默认: conversations_with_output.json)
    --timeout: 每条命令的超时时间，单位秒 (默认: 30)
    --start:   从第几个 conversation 开始 (从0开始计数，默认: 0)
    --end:     到第几个 conversation 结束 (不包含，默认: 全部)
"""

import json
import subprocess
import argparse
import os
import sys
from datetime import datetime


def execute_command(command: str, timeout: int = 30) -> str:
    """
    执行单条命令并返回输出结果
    
    Args:
        command: 要执行的命令
        timeout: 超时时间（秒）
    
    Returns:
        命令的标准输出和标准错误的组合
    """
    try:
        # 使用 shell=True 来执行命令，模拟真实终端环境
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy()
        )
        
        # 合并标准输出和标准错误
        output = result.stdout
        if result.stderr:
            if output:
                output += "\n" + result.stderr
            else:
                output = result.stderr
        
        return output.strip() if output else ""
    
    except subprocess.TimeoutExpired:
        return f"[命令执行超时: {timeout}秒]"
    except Exception as e:
        return f"[命令执行错误: {str(e)}]"


def process_conversations(input_file: str, output_file: str, timeout: int = 30, 
                          start_index: int = 0, end_index: int = None) -> None:
    """
    处理 conversations.json 文件，执行命令并填入输出
    
    Args:
        input_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径
        timeout: 命令超时时间
        start_index: 起始 conversation 索引
        end_index: 结束 conversation 索引（不包含）
    """
    # 读取 JSON 文件
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在读取文件: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_conversations = len(data)
    print(f"[INFO] 共有 {total_conversations} 个 conversations")
    
    # 设置处理范围
    if end_index is None or end_index > total_conversations:
        end_index = total_conversations
    
    print(f"[INFO] 处理范围: 第 {start_index} 个到第 {end_index - 1} 个 (共 {end_index - start_index} 个)")
    print("-" * 60)
    
    # 遍历每个 conversation
    for conv_idx in range(start_index, end_index):
        conversation = data[conv_idx]
        conversations_list = conversation.get("conversations", [])
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ========== Conversation {conv_idx + 1}/{end_index} ==========")
        
        # 每个 conversation 中有多轮对话 (human + gpt 成对出现)
        round_num = 0
        for i in range(0, len(conversations_list), 2):
            if i + 1 >= len(conversations_list):
                break
                
            human_entry = conversations_list[i]
            gpt_entry = conversations_list[i + 1]
            
            # 确保是 human -> gpt 的顺序
            if human_entry.get("from") != "human" or gpt_entry.get("from") != "gpt":
                print(f"  [警告] 第 {i} 条记录格式不正确，跳过")
                continue
            
            round_num += 1
            command = human_entry.get("value", "")
            
            print(f"  [轮次 {round_num}] 命令: {command}")
            
            # 执行命令
            output = execute_command(command, timeout)
            
            # 将输出填入 gpt 的 value
            gpt_entry["value"] = output
            
            # 显示输出预览（限制长度）
            preview = output[:200] + "..." if len(output) > 200 else output
            preview = preview.replace('\n', '\\n')
            print(f"  [轮次 {round_num}] 输出预览: {preview}")
        
        # 每处理10个 conversation 保存一次（防止中断丢失数据）
        if (conv_idx + 1) % 10 == 0:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 自动保存进度到: {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 最终保存
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 处理完成，保存到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"[INFO] 成功处理 {end_index - start_index} 个 conversations")


def main():
    parser = argparse.ArgumentParser(
        description='执行 conversations.json 中的命令并将输出填入对应的 gpt value 中'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='conversations.json',
        help='输入的 JSON 文件路径 (默认: conversations.json)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='conversations_with_output.json',
        help='输出的 JSON 文件路径 (默认: conversations_with_output.json)'
    )
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='每条命令的超时时间，单位秒 (默认: 30)'
    )
    parser.add_argument(
        '--start', '-s',
        type=int,
        default=0,
        help='从第几个 conversation 开始 (从0开始计数，默认: 0)'
    )
    parser.add_argument(
        '--end', '-e',
        type=int,
        default=None,
        help='到第几个 conversation 结束 (不包含，默认: 全部)'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        print(f"[错误] 输入文件不存在: {args.input}")
        sys.exit(1)
    
    print("=" * 60)
    print("Linux 命令执行脚本")
    print("=" * 60)
    print(f"输入文件: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"超时时间: {args.timeout} 秒")
    print("=" * 60)
    
    # 确认执行
    try:
        confirm = input("\n⚠️  警告: 此脚本将在系统上执行命令！\n确认执行? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("已取消执行")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n已取消执行")
        sys.exit(0)
    
    # 开始处理
    process_conversations(
        input_file=args.input,
        output_file=args.output,
        timeout=args.timeout,
        start_index=args.start,
        end_index=args.end
    )


if __name__ == "__main__":
    main()
