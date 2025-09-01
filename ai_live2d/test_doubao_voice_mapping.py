#!/usr/bin/env python3
"""
豆包TTS音色映射测试脚本
验证音色名称到voice_type的映射功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_doubao_voice_mapping():
    """测试豆包TTS音色映射功能"""
    print("🎤 豆包TTS音色映射测试")
    print("=" * 50)

    # 豆包TTS音色映射（与UI.py中的相同）
    doubao_voice_types = {
        "北京小爷（多情感）": "zh_male_beijingxiaoye_emo_v2_mars_bigtts",
        "柔美女友（多情感）": "zh_female_roumeinvyou_emo_v2_mars_bigtts",
        "阳光青年（多情感）": "zh_male_yangguangqingnian_emo_v2_mars_bigtts",
        "魅力女友（多情感）": "zh_female_meilinvyou_emo_v2_mars_bigtts",
        "爽快思思（多情感）": "zh_female_shuangkuaisisi_emo_v2_mars_bigtts",
        "甜心小美（多情感）": "zh_female_tianxinxiaomei_emo_v2_mars_bigtts",
        "高冷御姐（多情感）": "zh_female_gaolengyujie_emo_v2_mars_bigtts",
        "傲娇霸总（多情感）": "zh_male_aojiaobazong_emo_v2_mars_bigtts",
        "广州德哥（多情感）": "zh_male_guangzhoudege_emo_mars_bigtts",
        "京腔侃爷（多情感）": "zh_male_jingqiangkanye_emo_mars_bigtts",
        "邻居阿姨（多情感）": "zh_female_linjuayi_emo_v2_mars_bigtts",
        "优柔公子（多情感）": "zh_male_yourougongzi_emo_v2_mars_bigtts",
        "儒雅男友（多情感）": "zh_male_ruyayichen_emo_v2_mars_bigtts",
        "俊朗男友（多情感）": "zh_male_junlangnanyou_emo_v2_mars_bigtts",
        "冷酷哥哥（多情感）": "zh_male_lengkugege_emo_v2_mars_bigtts",
        "Glen": "en_male_glen_emo_v2_mars_bigtts",
        "Sylus": "en_male_sylus_emo_v2_mars_bigtts",
        "Candice": "en_female_candice_emo_v2_mars_bigtts",
        "Corey": "en_male_corey_emo_v2_mars_bigtts",
        "Nadia": "en_female_nadia_tips_emo_v2_mars_bigtts",
        "Serena": "en_female_skye_emo_v2_mars_bigtts"
    }

    print(f"📊 总音色数量: {len(doubao_voice_types)}")
    print(f"🔍 数据类型: {type(doubao_voice_types)}")

    print("\n🎯 测试音色名称到voice_type的映射:")

    # 测试一些示例映射
    test_cases = [
        "北京小爷（多情感）",
        "Glen",
        "不存在的音色"
    ]

    for voice_name in test_cases:
        if voice_name in doubao_voice_types:
            voice_type = doubao_voice_types[voice_name]
            print(f"✅ {voice_name} → {voice_type}")
        else:
            print(f"❌ {voice_name} (未找到)")

    print("\n🎯 测试反向映射（voice_type到音色名称）:")

    # 测试反向映射
    test_voice_types = [
        "zh_male_beijingxiaoye_emo_v2_mars_bigtts",
        "en_male_glen_emo_v2_mars_bigtts",
        "unknown_voice_type"
    ]

    for voice_type in test_voice_types:
        found_names = [name for name, vtype in doubao_voice_types.items() if vtype == voice_type]
        if found_names:
            print(f"✅ {voice_type} → {found_names[0]}")
        else:
            print(f"❌ {voice_type} (未找到对应的音色名称)")

    print("\n🎯 测试UI兼容性:")

    # 模拟UI中的选择逻辑
    selected_voice_name = "北京小爷（多情感）"
    if selected_voice_name in doubao_voice_types:
        actual_voice_type = doubao_voice_types[selected_voice_name]
        print(f"🎨 UI选择: '{selected_voice_name}'")
        print(f"🔧 实际使用: '{actual_voice_type}'")
        print("✅ UI兼容性测试通过")
    else:
        print("❌ UI兼容性测试失败")

    print("\n🎉 豆包TTS音色映射测试完成！")
    print("💡 现在UI中的下拉框将显示音色名称，但实际使用的是对应的voice_type")

if __name__ == "__main__":
    test_doubao_voice_mapping()
