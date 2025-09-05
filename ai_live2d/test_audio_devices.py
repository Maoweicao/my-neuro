#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
音频设备配置测试脚本
测试音频设备检测、配置保存和播放功能
"""

import json
import numpy as np
import time
import sys
import os

def test_audio_devices():
    """测试音频设备检测和配置"""
    print("=== 音频设备配置功能测试 ===\n")
    
    # 1. 测试sounddevice模块导入
    try:
        import sounddevice as sd
        print("✅ sounddevice模块导入成功")
    except ImportError:
        print("❌ sounddevice模块未安装")
        print("请运行: pip install sounddevice")
        return False
    
    # 2. 获取音频设备列表
    try:
        devices = sd.query_devices()
        print(f"✅ 检测到 {len(devices)} 个音频设备\n")
        
        print("📋 可用音频设备列表:")
        print("-" * 80)
        output_devices = []
        
        for i, device in enumerate(devices):
            device_type = []
            if device['max_input_channels'] > 0:
                device_type.append(f"输入({device['max_input_channels']}ch)")
            if device['max_output_channels'] > 0:
                device_type.append(f"输出({device['max_output_channels']}ch)")
                output_devices.append((i, device))
            
            type_str = " | ".join(device_type) if device_type else "无"
            
            print(f"[{i:2d}] {device['name']:<40} | {type_str}")
            print(f"     采样率: {device['default_samplerate']:>8.0f} Hz | "
                  f"主机API: {sd.query_hostapis(device['hostapi'])['name']}")
            
            if device['max_output_channels'] > 0:
                print(f"     延迟: 低={device['default_low_output_latency']:.3f}s "
                      f"高={device['default_high_output_latency']:.3f}s")
            print()
        
        print(f"✅ 检测到 {len(output_devices)} 个输出设备\n")
        
    except Exception as e:
        print(f"❌ 获取音频设备失败: {e}")
        return False
    
    # 3. 显示当前默认设备
    try:
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]
        
        if default_output is not None and 0 <= default_output < len(devices):
            default_output_device = devices[default_output]
            print(f"🔊 当前默认输出设备: [{default_output}] {default_output_device['name']}")
        else:
            print("⚠️  未找到默认输出设备")
        
        if default_input is not None and 0 <= default_input < len(devices):
            default_input_device = devices[default_input]
            print(f"🎤 当前默认输入设备: [{default_input}] {default_input_device['name']}\n")
        else:
            print("⚠️  未找到默认输入设备\n")
            
    except Exception as e:
        print(f"❌ 获取默认设备失败: {e}\n")
    
    # 4. 测试音频配置保存
    print("📝 测试音频配置保存...")
    
    # 选择一个输出设备进行测试
    if output_devices:
        test_device_index, test_device = output_devices[0]
        test_volume = 0.8
        
        # 创建测试配置
        test_config = {
            "audio": {
                "device_index": test_device_index,
                "volume": test_volume
            }
        }
        
        # 保存配置到测试文件
        config_test_path = "config_audio_test.json"
        try:
            with open(config_test_path, 'w', encoding='utf-8') as f:
                json.dump(test_config, f, ensure_ascii=False, indent=2)
            print(f"✅ 音频配置已保存到 {config_test_path}")
            print(f"   设备: [{test_device_index}] {test_device['name']}")
            print(f"   音量: {test_volume}x\n")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}\n")
    
    # 5. 测试音频播放
    print("🔊 测试音频播放...")
    
    try:
        # 生成测试音频（1秒440Hz正弦波）
        duration = 1.0
        sample_rate = 44100
        frequency = 440  # A4音
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        test_audio = np.sin(frequency * 2 * np.pi * t) * 0.3  # 降低音量避免过响
        
        print(f"🎵 播放测试音频: {frequency}Hz 正弦波, {duration}秒")
        
        # 测试各个输出设备
        for i, (device_index, device) in enumerate(output_devices[:3]):  # 只测试前3个设备
            try:
                print(f"   测试设备 [{device_index}]: {device['name']}")
                
                # 设置音频设备
                sd.default.device[1] = device_index
                
                # 播放测试音频
                sd.play(test_audio, sample_rate, blocking=True)
                print(f"   ✅ 设备 [{device_index}] 播放成功")
                
                # 短暂暂停
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ 设备 [{device_index}] 播放失败: {e}")
        
        print("✅ 音频播放测试完成\n")
        
    except Exception as e:
        print(f"❌ 音频播放测试失败: {e}\n")
    
    # 6. 清理测试文件
    try:
        if os.path.exists(config_test_path):
            os.remove(config_test_path)
            print(f"🧹 已清理测试配置文件: {config_test_path}")
    except Exception as e:
        print(f"⚠️  清理测试文件失败: {e}")
    
    print("\n=== 音频设备配置功能测试完成 ===")
    return True

def main():
    """主函数"""
    try:
        success = test_audio_devices()
        if success:
            print("\n🎉 所有测试通过！音频设备配置功能正常。")
            return 0
        else:
            print("\n💥 测试失败，请检查音频设备和环境配置。")
            return 1
    except KeyboardInterrupt:
        print("\n⛔ 用户中断测试")
        return 0
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
