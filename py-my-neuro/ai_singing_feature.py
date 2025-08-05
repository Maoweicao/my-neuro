import os
import random
import threading
import pygame
import keyboard
import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger("singing_system")


class SingingSystem:
    """AI唱歌系统 - 处理歌曲播放和口型同步"""

    def __init__(self, live_model=None, audio_dir="KTV/output"):
        self.live_model = live_model
        self.audio_dir = audio_dir
        self.is_singing = False
        self.current_song = None
        self.vocal_thread = None
        self.acc_thread = None

        # 注册快捷键
        keyboard.add_hotkey('ctrl+shift+1', self.start_random_song)
        keyboard.add_hotkey('ctrl+shift+2', self.stop_singing)

        logger.info("AI唱歌系统初始化完成")

    def get_available_songs(self):
        """获取可用的歌曲列表（必须同时有Vocal和Acc文件）"""
        if not os.path.exists(self.audio_dir):
            logger.warning(f"音频目录不存在: {self.audio_dir}")
            return []

        songs = {}

        # 扫描目录中的所有wav文件
        for file in os.listdir(self.audio_dir):
            if not file.endswith('.wav'):
                continue

            # 解析文件名
            if file.endswith('-Vocal.wav'):
                song_name = file[:-10]  # 移除'-Vocal.wav'
                if song_name not in songs:
                    songs[song_name] = {}
                songs[song_name]['vocal'] = os.path.join(self.audio_dir, file)

            elif file.endswith('-Acc.wav'):
                song_name = file[:-8]  # 移除'-Acc.wav'
                if song_name not in songs:
                    songs[song_name] = {}
                songs[song_name]['acc'] = os.path.join(self.audio_dir, file)

        # 只返回同时有vocal和acc文件的完整歌曲
        complete_songs = []
        for song_name, files in songs.items():
            if 'vocal' in files and 'acc' in files:
                # 验证文件确实存在
                if os.path.exists(files['vocal']) and os.path.exists(files['acc']):
                    complete_songs.append({
                        'name': song_name,
                        'vocal_path': files['vocal'],
                        'acc_path': files['acc']
                    })
                    logger.debug(f"找到完整歌曲: {song_name}")
                else:
                    logger.warning(f"歌曲文件缺失: {song_name}")
            else:
                logger.warning(f"歌曲不完整: {song_name} (缺少{'vocal' if 'vocal' not in files else 'acc'}文件)")

        logger.info(f"找到 {len(complete_songs)} 首完整歌曲")
        return complete_songs

    def start_random_song(self):
        """开始随机播放歌曲"""
        if self.is_singing:
            logger.info("已经在唱歌中，先停止当前歌曲")
            self.stop_singing()

        # 获取可用歌曲
        available_songs = self.get_available_songs()
        if not available_songs:
            logger.warning("没有找到可用的歌曲文件")
            print("🎵 没有找到可用的歌曲文件！请检查KTV/output目录")
            return

        # 随机选择一首歌
        selected_song = random.choice(available_songs)
        self.current_song = selected_song

        logger.info(f"开始播放歌曲: {selected_song['name']}")
        print(f"🎵 开始播放: {selected_song['name']}")

        # 🎯 新增：播放麦克风出现动作（第1个动作，索引为0）
        if self.live_model:
            try:
                self.live_model.play_tapbody_motion(0)  # 播放麦克风出现动作
                print("🎤 麦克风出现！")
            except Exception as e:
                logger.error(f"播放麦克风动作失败: {e}")

        # 设置唱歌状态
        self.is_singing = True

        # 同时启动vocal和acc播放
        self.start_dual_audio_playback(selected_song)

    def start_dual_audio_playback(self, song_info):
        """同时播放人声和伴奏"""

        def audio_playback_thread():
            try:
                # 初始化pygame mixer，设置多个通道
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.set_num_channels(8)  # 设置8个通道

                # 加载音频文件
                vocal_sound = pygame.mixer.Sound(song_info['vocal_path'])
                acc_sound = pygame.mixer.Sound(song_info['acc_path'])

                # 同时播放两个音频
                vocal_channel = vocal_sound.play()
                acc_channel = acc_sound.play()

                # 启动口型同步，设置更大的强度
                if self.live_model:
                    # 临时调高口型同步强度
                    original_intensity = getattr(self.live_model, 'lip_sync_intensity', 3.0)
                    self.live_model.lip_sync_intensity = 8.0  # 调大到8倍

                    self.live_model.start_lip_sync(song_info['vocal_path'])

                print(f"🎵 同时播放人声和伴奏: {song_info['name']}")

                # 等待播放完成，但要经常检查is_singing状态
                while (vocal_channel.get_busy() or acc_channel.get_busy()) and self.is_singing:
                    time.sleep(0.1)  # 每100ms检查一次状态

                    # 如果被手动停止，立即停止播放
                    if not self.is_singing:
                        vocal_channel.stop()
                        acc_channel.stop()
                        break

                # 播放完成
                if self.is_singing:  # 只有在自然播放完成时才调用
                    self.on_song_finished()

            except Exception as e:
                logger.error(f"播放失败: {e}")
                print(f"❌ 播放失败: {e}")
                # 确保停止状态
                self.is_singing = False

        # 在新线程中播放音频，避免阻塞主线程
        audio_thread = threading.Thread(target=audio_playback_thread, daemon=True)
        audio_thread.start()

    def stop_singing(self):
        """停止唱歌"""
        if not self.is_singing:
            return

        logger.info("停止唱歌")
        print("🛑 停止唱歌")

        # 设置停止标志
        self.is_singing = False

        # 强制停止所有pygame音频播放
        try:
            if pygame.mixer.get_init():
                pygame.mixer.stop()  # 停止所有音频通道
                pygame.mixer.music.stop()  # 停止音乐播放

                # 强制清理所有通道
                for i in range(pygame.mixer.get_num_channels()):
                    channel = pygame.mixer.Channel(i)
                    if channel.get_busy():
                        channel.stop()

            print("🔇 所有音频已停止")
        except Exception as e:
            logger.error(f"停止音频失败: {e}")

        # 停止口型同步
        if self.live_model:
            try:
                self.live_model.stop_lip_sync()
                print("👄 口型同步已停止")
            except Exception as e:
                logger.error(f"停止口型同步失败: {e}")

        # 🎯 新增：播放麦克风收起动作（第9个动作，索引为8）
        if self.live_model:
            try:
                self.live_model.play_tapbody_motion(1)  # 播放麦克风收起动作（Ctrl+9对应）
                print("🎤 麦克风收起！")
            except Exception as e:
                logger.error(f"播放麦克风收起动作失败: {e}")

        # 清理状态
        self.current_song = None
        self.vocal_thread = None
        self.acc_thread = None

        logger.info("唱歌已停止")

        # 停止口型同步
        if self.live_model:
            try:
                self.live_model.stop_lip_sync()
                print("👄 口型同步已停止")
            except Exception as e:
                logger.error(f"停止口型同步失败: {e}")

        # 🎯 新增：播放麦克风收起动作（第10个动作，索引为9）
        if self.live_model:
            try:
                self.live_model.play_tapbody_motion(9)  # 播放麦克风收起动作
                print("🎤 麦克风收起！")
            except Exception as e:
                logger.error(f"播放麦克风收起动作失败: {e}")

        # 清理状态
        self.current_song = None
        self.vocal_thread = None
        self.acc_thread = None

        logger.info("唱歌已停止")

    def on_song_finished(self):
        """歌曲播放完成回调"""
        logger.info(f"歌曲播放完成: {self.current_song['name'] if self.current_song else 'Unknown'}")
        print(f"✅ 歌曲播放完成: {self.current_song['name'] if self.current_song else 'Unknown'}")

        # 重置状态
        self.is_singing = False
        self.current_song = None

    def get_current_song_info(self):
        """获取当前播放的歌曲信息"""
        if self.is_singing and self.current_song:
            return {
                'name': self.current_song['name'],
                'is_singing': True
            }
        return {'is_singing': False}

    def list_available_songs(self):
        """列出所有可用的歌曲"""
        songs = self.get_available_songs()
        if not songs:
            print("🎵 没有找到可用的歌曲")
            return

        print("🎵 可用歌曲列表:")
        for i, song in enumerate(songs, 1):
            print(f"  {i}. {song['name']}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 测试唱歌系统
    print("🎵 AI唱歌系统测试")

    # 创建唱歌系统
    singing_system = SingingSystem()

    # 列出可用歌曲
    singing_system.list_available_songs()

    print("\n快捷键说明:")
    print("Ctrl+Shift+1: 开始随机播放歌曲")
    print("Ctrl+Shift+2: 停止唱歌")
    print("按任意键退出...")

    try:
        input()
    except KeyboardInterrupt:
        pass

    # 清理
    singing_system.stop_singing()
