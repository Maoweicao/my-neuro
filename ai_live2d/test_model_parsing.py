#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模型文件解析
"""

import os
import json
import sys

def test_model_parsing(model_path):
    """测试模型文件解析"""
    print(f"🔍 测试模型文件: {model_path}")
    
    if not os.path.exists(model_path):
        print("❌ 文件不存在")
        return False
    
    try:
        # 检查文件大小
        file_size = os.path.getsize(model_path)
        print(f"📄 文件大小: {file_size} bytes ({file_size / 1024:.1f} KB)")
        
        # 检查文件权限
        readable = os.access(model_path, os.R_OK)
        print(f"🔓 文件可读: {readable}")
        
        if not readable:
            print("❌ 文件无读取权限")
            return False
        
        # 读取并解析JSON
        with open(model_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            print("❌ 文件内容为空")
            return False
        
        print(f"📝 内容长度: {len(content)} 字符")
        
        # 解析JSON
        model_data = json.loads(content)
        print("✅ JSON解析成功")
        
        # 显示基本信息
        version = model_data.get('Version', '未知')
        print(f"📋 模型版本: {version}")
        
        # 文件引用信息
        file_refs = model_data.get('FileReferences', {})
        moc_file = file_refs.get('Moc', '未找到')
        textures = file_refs.get('Textures', [])
        expressions = file_refs.get('Expressions', [])
        motions = file_refs.get('Motions', {})
        
        print(f"🎯 Moc文件: {moc_file}")
        print(f"🖼️ 纹理数量: {len(textures)}")
        print(f"😊 表情数量: {len(expressions)}")
        print(f"🎬 动作组数量: {len(motions)}")
        
        # 详细表情信息
        if expressions:
            print("📝 表情列表:")
            for i, expr in enumerate(expressions[:5]):  # 只显示前5个
                if isinstance(expr, dict):
                    name = expr.get('Name', expr.get('File', f'表情{i}'))
                    print(f"  - {name}")
                elif isinstance(expr, str):
                    print(f"  - {os.path.splitext(os.path.basename(expr))[0]}")
            if len(expressions) > 5:
                print(f"  ... 还有 {len(expressions) - 5} 个表情")
        
        # 详细动作信息
        if motions:
            print("📝 动作组列表:")
            for group_name, motion_list in list(motions.items())[:5]:  # 只显示前5个
                count = len(motion_list) if isinstance(motion_list, list) else 1
                print(f"  - {group_name}: {count}个动作")
            if len(motions) > 5:
                print(f"  ... 还有 {len(motions) - 5} 个动作组")
        
        print("✅ 模型文件解析完成，没有发现问题")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return False

def main():
    """主函数"""
    # 测试之前出错的模型文件
    model_path = "F:/my-neuro/live-2d/2D/maolili~_vts/mailili.model3.json"
    
    print("=" * 60)
    print("Live2D模型文件解析测试")
    print("=" * 60)
    
    success = test_model_parsing(model_path)
    
    print("=" * 60)
    if success:
        print("🎉 测试通过！模型文件可以正常解析")
        print("现在可以使用备用解析方法加载模型详情")
    else:
        print("⚠️ 测试失败，需要检查模型文件")
    print("=" * 60)

if __name__ == "__main__":
    main()
