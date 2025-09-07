#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live2D模型加载和预览功能综合测试
测试修复后的模型加载功能和新增的预览功能
"""

import sys
import os
import json
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_model_loading_fix():
    """测试模型加载修复"""
    print("\n" + "="*50)
    print("🔧 测试模型加载修复")
    print("="*50)
    
    try:
        from UI import Widget
        
        # 创建UI实例
        ui = Widget()
        
        # 测试模型路径
        model_path = "F:/my-neuro/live-2d/2D/maolili~_vts/mailili.model3.json"
        
        if os.path.exists(model_path):
            print(f"📂 测试模型: {model_path}")
            
            # 调用备用解析方法
            try:
                ui.load_model_details_fallback(model_path)
                print("✅ 备用解析方法工作正常")
                return True
            except Exception as e:
                print(f"❌ 备用解析方法失败: {e}")
                return False
        else:
            print(f"⚠️ 测试模型文件不存在: {model_path}")
            # 使用示例模型测试
            return test_with_sample_model(ui)
            
    except Exception as e:
        print(f"❌ 模型加载测试失败: {e}")
        return False

def test_with_sample_model(ui):
    """使用示例模型测试"""
    print("📄 创建示例模型进行测试...")
    
    # 创建示例模型数据
    sample_data = {
        "Version": 3,
        "FileReferences": {
            "Moc": "sample.moc3",
            "Textures": ["texture_00.png"],
            "Expressions": [
                {"Name": "happy", "File": "expressions/happy.exp3.json"},
                {"Name": "sad", "File": "expressions/sad.exp3.json"}
            ],
            "Motions": {
                "Idle": [{"File": "motions/idle.motion3.json"}],
                "TapHead": [{"File": "motions/tap_head.motion3.json"}]
            }
        },
        "Layout": {
            "CenterX": 0.0,
            "CenterY": 0.0,
            "Width": 2.0,
            "Height": 2.0
        }
    }
    
    # 保存示例文件
    sample_path = "test_sample_model.model3.json"
    try:
        with open(sample_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 示例模型文件创建成功: {sample_path}")
        
        # 测试备用解析
        ui.load_model_details_fallback(os.path.abspath(sample_path))
        print("✅ 示例模型解析成功")
        
        # 清理
        os.remove(sample_path)
        return True
        
    except Exception as e:
        print(f"❌ 示例模型测试失败: {e}")
        if os.path.exists(sample_path):
            os.remove(sample_path)
        return False

def test_preview_window():
    """测试预览窗口功能"""
    print("\n" + "="*50)
    print("🎭 测试Live2D预览窗口")
    print("="*50)
    
    try:
        from PyQt5.QtWidgets import QApplication
        from UI import Live2DPreviewWindow
        
        # 创建应用（如果不存在）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # 创建测试模型文件
        test_model_data = {
            "Version": 3,
            "FileReferences": {
                "Moc": "test.moc3",
                "Textures": ["texture_00.png", "texture_01.png"],
                "Expressions": [
                    {"Name": "happy", "File": "expressions/happy.exp3.json"},
                    {"Name": "sad", "File": "expressions/sad.exp3.json"},
                    {"Name": "surprised", "File": "expressions/surprised.exp3.json"}
                ],
                "Motions": {
                    "Idle": [
                        {"File": "motions/idle_01.motion3.json"},
                        {"File": "motions/idle_02.motion3.json"}
                    ],
                    "TapHead": [{"File": "motions/tap_head.motion3.json"}],
                    "Greeting": [{"File": "motions/greeting.motion3.json"}]
                }
            },
            "Layout": {
                "CenterX": 0.0,
                "CenterY": 0.0,
                "Width": 2.0,
                "Height": 3.0
            }
        }
        
        test_model_path = "test_preview_model.model3.json"
        
        try:
            # 保存测试模型
            with open(test_model_path, 'w', encoding='utf-8') as f:
                json.dump(test_model_data, f, indent=2, ensure_ascii=False)
            
            print(f"📄 测试模型文件: {test_model_path}")
            
            # 创建预览窗口（不显示）
            preview_window = Live2DPreviewWindow(os.path.abspath(test_model_path))
            
            # 验证窗口创建成功
            if preview_window.windowTitle():
                print("✅ 预览窗口创建成功")
                print(f"📋 窗口标题: {preview_window.windowTitle()}")
                
                # 测试模型信息加载
                if hasattr(preview_window, 'info_browser'):
                    print("✅ 信息面板创建成功")
                
                if hasattr(preview_window, 'expr_list'):
                    expr_count = preview_window.expr_list.count()
                    print(f"😊 表情列表项数: {expr_count}")
                
                if hasattr(preview_window, 'motion_list'):
                    motion_count = preview_window.motion_list.count()
                    print(f"🎬 动作列表项数: {motion_count}")
                
                print("✅ 预览窗口功能测试通过")
                return True
            else:
                print("❌ 预览窗口创建失败")
                return False
                
        finally:
            # 清理测试文件
            if os.path.exists(test_model_path):
                os.remove(test_model_path)
                
    except Exception as e:
        print(f"❌ 预览窗口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """集成测试"""
    print("\n" + "="*50)
    print("🔗 集成功能测试")
    print("="*50)
    
    try:
        # 测试主界面预览按钮功能
        from UI import Widget
        from PyQt5.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        ui = Widget()
        
        # 检查预览按钮是否存在
        if hasattr(ui, 'preview_live2d_btn'):
            print("✅ 预览按钮已添加到主界面")
            
            # 检查按钮属性
            btn = ui.preview_live2d_btn
            print(f"📋 按钮文本: {btn.text()}")
            print(f"🔧 按钮工具提示: {btn.toolTip()}")
            print(f"⚡ 按钮启用状态: {btn.isEnabled()}")
            
            return True
        else:
            print("❌ 预览按钮未找到")
            return False
            
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 Live2D模型加载和预览功能综合测试")
    print("测试时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    results = []
    
    # 运行测试
    tests = [
        ("模型加载修复", test_model_loading_fix),
        ("预览窗口功能", test_preview_window),
        ("集成功能", test_integration)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} : {status}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！功能修复和新增功能都正常工作")
        print("\n💡 使用说明:")
        print("1. 模型加载错误已修复，使用了更可靠的JSON直接解析方法")
        print("2. 新增了Live2D预览窗口功能，可以查看模型信息和列表")
        print("3. 预览按钮已添加到Live2D配置页面")
    else:
        print(f"⚠️ {total - passed} 项测试失败，需要进一步检查")
    
    print("="*60)

if __name__ == "__main__":
    main()
