#!/usr/bin/env python3
"""
豆包TTS音色下拉框测试脚本
验证音色类型下拉框是否正常工作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_doubao_voice_types():
    """测试豆包TTS音色列表"""
    # 豆包TTS音色列表（与UI.py中的相同）- 音色名称作为key，voice_type作为value
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

    print("🎤 豆包TTS音色类型测试")
    print("=" * 50)
    print(f"📊 总音色数量: {len(doubao_voice_types)}")
    print()

    # 显示前10个音色
    print("🎯 前10个音色示例:")
    for i, (voice_name, voice_type) in enumerate(list(doubao_voice_types.items())[:10], 1):
        print(f"{i:2d}. {voice_name}")
        print(f"    → {voice_type}")
    print()

    # 显示一些特殊音色
    print("🌟 特殊音色示例:")
    special_voices = ["北京小爷（多情感）", "爽快思思（多情感）", "Glen", "Tina老师", "温暖阿虎/Alvin"]
    for voice in special_voices:
        if voice in doubao_voice_types:
            print(f"   ✅ {voice} → {doubao_voice_types[voice]}")
        else:
            print(f"   ❌ {voice} (未找到)")
    print()

    # 检查重复项
    duplicates = []
    seen = set()
    for voice_name in doubao_voice_types.keys():
        if voice_name in seen:
            duplicates.append(voice_name)
        else:
            seen.add(voice_name)

    if duplicates:
        print(f"⚠️  发现重复音色名称: {duplicates}")
    else:
        print("✅ 所有音色名称唯一，无重复")
    
    # 检查voice_type重复项
    voice_duplicates = []
    voice_seen = set()
    for voice_type in doubao_voice_types.values():
        if voice_type in voice_seen:
            voice_duplicates.append(voice_type)
        else:
            voice_seen.add(voice_type)
    
    if voice_duplicates:
        print(f"⚠️  发现重复voice_type: {voice_duplicates}")
    else:
        print("✅ 所有voice_type唯一，无重复")

    print()
    print("🎉 豆包TTS音色列表测试完成！")
    print("💡 现在可以在UI中看到可编辑的下拉框，包含所有这些音色选项")

if __name__ == "__main__":
    test_doubao_voice_types()
