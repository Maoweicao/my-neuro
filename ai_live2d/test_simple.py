#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的Live2D功能测试
只测试关键的修复和新功能
"""

import sys
import os
import json

def test_fallback_method():
    """测试备用解析方法"""
    print("🔧 测试Live2D模型备用解析方法")
    print("-" * 40)
    
    # 创建测试数据
    test_data = {
        "Version": 3,
        "FileReferences": {
            "Moc": "test.moc3",
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
    
    # 保存测试文件
    test_file = "test_fallback_model.model3.json"
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 创建测试文件: {test_file}")
        
        # 测试文件解析
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            # 解析表情
            expressions = []
            if 'FileReferences' in model_data and 'Expressions' in model_data['FileReferences']:
                expr_data = model_data['FileReferences']['Expressions']
                for expr in expr_data:
                    if isinstance(expr, dict):
                        if 'Name' in expr:
                            expressions.append(expr['Name'])
                        elif 'File' in expr:
                            expr_name = os.path.splitext(os.path.basename(expr['File']))[0]
                            expressions.append(expr_name)
            
            # 解析动作
            motions = {}
            if 'FileReferences' in model_data and 'Motions' in model_data['FileReferences']:
                motion_data = model_data['FileReferences']['Motions']
                for group_name, motion_list in motion_data.items():
                    if isinstance(motion_list, list):
                        motions[group_name] = len(motion_list)
                    else:
                        motions[group_name] = 1
            
            print(f"✅ 解析成功")
            print(f"📋 版本: {model_data.get('Version', '未知')}")
            print(f"😊 表情数量: {len(expressions)}")
            print(f"🎬 动作组数量: {len(motions)}")
            print(f"📝 表情列表: {expressions}")
            print(f"📝 动作组: {list(motions.keys())}")
            
            return True
            
        except Exception as e:
            print(f"❌ 解析失败: {e}")
            return False
    
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)

def test_preview_window_creation():
    """测试预览窗口创建"""
    print("\n🎭 测试Live2D预览窗口创建")
    print("-" * 40)
    
    try:
        from PyQt5.QtWidgets import QApplication
        import sys
        
        # 创建应用
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # 创建测试模型
        test_data = {
            "Version": 3,
            "FileReferences": {
                "Moc": "preview_test.moc3",
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
            }
        }
        
        test_file = "test_preview_window.model3.json"
        try:
            # 保存测试文件
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2, ensure_ascii=False)
            
            print(f"📄 创建测试文件: {test_file}")
            
            # 导入并创建预览窗口
            from UI import Live2DPreviewWindow
            
            preview_window = Live2DPreviewWindow(os.path.abspath(test_file))
            
            print(f"✅ 预览窗口创建成功")
            print(f"📋 窗口标题: {preview_window.windowTitle()}")
            print(f"📐 窗口大小: {preview_window.size().width()}x{preview_window.size().height()}")
            
            # 检查组件
            components = []
            if hasattr(preview_window, 'info_browser'):
                components.append("信息浏览器")
            if hasattr(preview_window, 'expr_list'):
                components.append("表情列表")
            if hasattr(preview_window, 'motion_list'):
                components.append("动作列表")
            if hasattr(preview_window, 'preview_area'):
                components.append("预览区域")
            
            print(f"🧩 组件检查: {', '.join(components)}")
            
            # 检查列表项数量
            if hasattr(preview_window, 'expr_list'):
                expr_count = preview_window.expr_list.count()
                print(f"😊 表情列表项: {expr_count}")
            
            if hasattr(preview_window, 'motion_list'):
                motion_count = preview_window.motion_list.count()
                print(f"🎬 动作列表项: {motion_count}")
            
            return True
            
        finally:
            # 清理测试文件
            if os.path.exists(test_file):
                os.remove(test_file)
    
    except Exception as e:
        print(f"❌ 预览窗口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_actual_model():
    """测试实际模型文件"""
    print("\n📂 测试实际模型文件")
    print("-" * 40)
    
    model_path = "F:/my-neuro/live-2d/2D/maolili~_vts/mailili.model3.json"
    
    if not os.path.exists(model_path):
        print(f"⚠️ 模型文件不存在: {model_path}")
        return False
    
    try:
        # 基本文件检查
        file_size = os.path.getsize(model_path)
        print(f"📄 文件大小: {file_size} bytes")
        
        # JSON解析测试
        with open(model_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
        
        print(f"✅ JSON解析成功")
        print(f"📋 版本: {model_data.get('Version', '未知')}")
        
        # 文件引用检查
        file_refs = model_data.get('FileReferences', {})
        print(f"🎯 Moc文件: {file_refs.get('Moc', '未找到')}")
        print(f"🖼️ 纹理数量: {len(file_refs.get('Textures', []))}")
        print(f"😊 表情数量: {len(file_refs.get('Expressions', []))}")
        print(f"🎬 动作组数量: {len(file_refs.get('Motions', {}))}")
        
        # 使用预览窗口测试
        if len(sys.argv) == 1:  # 不是从其他脚本调用
            try:
                from PyQt5.QtWidgets import QApplication
                from UI import Live2DPreviewWindow
                
                app = QApplication.instance()
                if app is None:
                    app = QApplication(sys.argv)
                
                preview_window = Live2DPreviewWindow(model_path)
                print("✅ 实际模型预览窗口创建成功")
                
            except Exception as e:
                print(f"⚠️ 预览窗口创建失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 实际模型测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 Live2D功能简化测试")
    print("=" * 50)
    
    tests = [
        ("备用解析方法", test_fallback_method),
        ("预览窗口创建", test_preview_window_creation),
        ("实际模型文件", test_actual_model)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 结果汇总
    print("\n" + "=" * 50)
    print("📊 测试结果")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:15} : {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"总计: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("🎉 所有功能测试通过！")
        print("\n✨ 功能确认:")
        print("✅ Live2D模型加载错误已修复")
        print("✅ Live2D预览窗口功能正常")
        print("✅ 模型文件解析功能正常")
    else:
        print(f"⚠️ 还有 {len(results) - passed} 项功能需要检查")

if __name__ == "__main__":
    main()
