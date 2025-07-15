#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import glob
import subprocess


def main():
    # 获取当前目录作为搜索路径
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 在当前目录下查找pth模型文件
    pth_files = glob.glob(os.path.join(current_dir, "*.pth"))

    if not pth_files:
        print("错误: 当前目录下未找到pth模型文件!")
        print("请将pth模型文件放在当前脚本所在目录下")
        return

    model_path = pth_files[0]
    print(f"找到模型文件: {os.path.basename(model_path)}")

    # 在当前目录下查找wav音频文件
    wav_files = glob.glob(os.path.join(current_dir, "*.wav"))

    if not wav_files:
        print("错误: 当前目录下未找到wav音频文件!")
        print("请将wav音频文件放在当前脚本所在目录下")
        return

    # 直接使用找到的第一个wav文件
    reference_audio = wav_files[0]
    print(f"\n找到参考音频文件: {os.path.basename(reference_audio)}")

    # 获取用户输入
    print("\n请输入以下信息生成TTS命令:")

    # 默认值
    default_device = "cuda"
    default_port = "5000"
    default_language = "zh"

    # 获取文本内容
    text = input("请输入要合成的文本内容: ")
    if not text:
        print("错误: 文本内容不能为空!")
        return

    # 语言选项及说明
    print("\n可选语言代码:")
    print("  zh - 中文")
    print("  en - 英文")
    print("  ja - 日语")
    print("  ko - 韩语")

    # 获取语言
    language = input(f"请输入语言代码 (默认: {default_language}): ") or default_language

    # 生成命令
    cmd = (f"python tts_api.py -p {default_port} -d {default_device} "
           f"-s {model_path} -dr {reference_audio} -dt \"{text}\" -dl {language}")

    # 创建bat文件
    bat_filename = "你的TTS.bat"
    bat_path = os.path.join(current_dir, bat_filename)

    # 写入bat文件内容 - 使用ANSI编码
    with open(bat_path, "w", encoding="gbk") as bat_file:
        bat_file.write("@echo off\n")
        bat_file.write("call conda activate my-neuro\n")
        bat_file.write("cd ..\n")  # 添加返回上一级目录的命令
        bat_file.write(f"{cmd}\n")
        bat_file.write("pause\n")

    print(f"\n已生成批处理文件: {bat_filename}")
    print("您可以双击此文件执行TTS命令")


if __name__ == "__main__":
    main()
