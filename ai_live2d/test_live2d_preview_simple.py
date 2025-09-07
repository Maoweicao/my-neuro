#!/usr/bin/env python3
# coding:utf-8

import sys
import os
sys.path.append(os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from UI import Live2DPreviewWidget

def test_live2d_preview():
    """测试Live2D预览组件"""
    print("开始测试Live2DPreviewWidget...")
    
    # 创建QApplication
    app = QApplication(sys.argv)
    
    # 测试模型路径
    model_path = r"f:\my-neuro\ai_live2d\models\2D\肥牛"
    print(f"测试模型路径: {model_path}")
    print(f"路径存在: {os.path.exists(model_path)}")
    
    # 手动查找纹理文件
    texture_files = []
    for root, dirs, files in os.walk(model_path):
        print(f"扫描目录: {root}")
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                full_path = os.path.join(root, file)
                texture_files.append(full_path)
                print(f"找到纹理文件: {full_path}")
    
    print(f"手动查找结果: {len(texture_files)} 个文件")
    
    # 创建预览组件
    try:
        preview = Live2DPreviewWidget(model_path)
        print(f"✅ Live2DPreviewWidget创建成功")
        
        # 手动调用load_model
        preview.load_model(model_path)
        
        print(f"模型路径: {preview.model_path}")
        print(f"纹理帧数量: {len(preview.texture_frames)}")
        
        if preview.texture_frames:
            print("找到的纹理文件:")
            for i, frame in enumerate(preview.texture_frames):
                print(f"  {i}: {os.path.basename(frame)}")
        
        # 测试表情设置
        preview.set_expression("happy")
        print("✅ 表情设置测试完成")
        
        # 测试动作播放
        preview.play_motion("test_motion")
        print("✅ 动作播放测试完成")
        
        # 测试停止
        preview.stop_motion()
        print("✅ 停止动作测试完成")
        
        print("🎉 所有测试通过！Live2D动态预览组件工作正常")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 退出应用
    app.quit()

if __name__ == '__main__':
    test_live2d_preview()
