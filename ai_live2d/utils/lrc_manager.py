#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LRC歌词管理器
解析LRC格式歌词文件并按时间顺序显示歌词
"""

import re
import time
import threading
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger("lrc_manager")

class LyricLine:
    """歌词行数据类"""
    
    def __init__(self, time_ms: int, text: str):
        self.time_ms = time_ms  # 时间戳（毫秒）
        self.text = text.strip()  # 歌词文本
        
    def __repr__(self):
        return f"LyricLine({self.time_ms}ms, '{self.text}')"
    
    def __lt__(self, other):
        return self.time_ms < other.time_ms

class LRCParser:
    """LRC歌词解析器"""
    
    @staticmethod
    def parse_time(time_str: str) -> int:
        """解析时间字符串为毫秒
        
        Args:
            time_str: 时间字符串，格式如 "02:15.30"、"02:15.300"、"02:15" 或 "00:02:15"
            
        Returns:
            int: 毫秒数
        """
        try:
            # 支持格式：[hh:mm:ss]、[mm:ss.xx]、[mm:ss.xxx] 或 [mm:ss]
            
            # 首先尝试特殊的 mm:ss:ms 格式 (如 00:07:00，表示7秒0毫秒)
            # 这是一些LRC文件的非标准格式，第三部分实际表示毫秒/百分秒
            match = re.match(r'(\d{1,2}):(\d{2}):(\d{2})', time_str)
            if match:
                first = int(match.group(1))
                second = int(match.group(2))
                third = int(match.group(3))
                
                # 判断是否为 mm:ss:ms 格式：
                # 如果第一部分小于60且第二部分也小于60，可能是 mm:ss:ms 格式
                if first < 60 and second < 60:
                    # 检查第三部分：如果是0或小于100，可能是毫秒/百分秒
                    if third <= 99:
                        # 按照 mm:ss:centiseconds 格式解析
                        total_ms = first * 60 * 1000 + second * 1000 + third * 10
                        logger.debug(f"解析时间戳 {time_str} 为 mm:ss:cs 格式: {total_ms}ms")
                        return total_ms
                
                # 标准的 hh:mm:ss 格式
                total_ms = first * 60 * 60 * 1000 + second * 60 * 1000 + third * 1000
                logger.debug(f"解析时间戳 {time_str} 为 hh:mm:ss 格式: {total_ms}ms")
                return total_ms
            
            # 然后尝试带毫秒的格式 mm:ss.xx
            match = re.match(r'(\d{1,2}):(\d{2})\.(\d{2,3})', time_str)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                centiseconds_str = match.group(3)
                
                # 处理毫秒部分（可能是2位或3位）
                if len(centiseconds_str) == 2:
                    # 2位数，代表百分之一秒
                    milliseconds = int(centiseconds_str) * 10
                else:
                    # 3位数，直接是毫秒
                    milliseconds = int(centiseconds_str)
                
                total_ms = minutes * 60 * 1000 + seconds * 1000 + milliseconds
                logger.debug(f"解析时间戳 {time_str} 为 mm:ss.xxx 格式: {total_ms}ms")
                return total_ms
            
            # 最后尝试不带毫秒的格式 [mm:ss]
            match = re.match(r'(\d{1,2}):(\d{2})', time_str)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                total_ms = minutes * 60 * 1000 + seconds * 1000
                logger.debug(f"解析时间戳 {time_str} 为 mm:ss 格式: {total_ms}ms")
                return total_ms
            
            logger.warning(f"无法解析时间格式: {time_str}")
            return 0
            
        except Exception as e:
            logger.warning(f"解析时间失败: {time_str}, 错误: {e}")
            return 0
    
    @staticmethod
    def parse_lrc_content(lrc_content: str) -> Tuple[List[LyricLine], Dict[str, str]]:
        """解析LRC歌词内容
        
        Args:
            lrc_content: LRC文件内容
            
        Returns:
            Tuple[List[LyricLine], Dict[str, str]]: 歌词行列表和元数据
        """
        lyrics = []
        metadata = {}
        
        if not lrc_content:
            logger.warning("LRC内容为空")
            return lyrics, metadata
        
        logger.info(f"开始解析LRC内容，长度: {len(lrc_content)} 字符")
        logger.info(f"LRC内容前500字符: {lrc_content[:500]}")
        
        lines = lrc_content.strip().split('\n')
        logger.info(f"分割后得到 {len(lines)} 行内容")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            logger.debug(f"处理第 {i+1} 行: {line}")
            
            # 解析元数据标签 [tag:value]
            metadata_match = re.match(r'\[([a-zA-Z]+):(.+)\]', line)
            if metadata_match:
                tag = metadata_match.group(1).lower()
                value = metadata_match.group(2).strip()
                metadata[tag] = value
                logger.debug(f"解析到元数据: {tag} = {value}")
                continue
            
            # 解析时间戳和歌词 [hh:mm:ss]、[mm:ss.xx]歌词文本 或 [mm:ss]歌词文本
            # 支持多种时间格式
            time_matches = re.findall(r'\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{2,3})?)\]', line)
            if time_matches:
                # 提取歌词文本（去掉所有时间标签）
                text = re.sub(r'\[\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{2,3})?\]', '', line).strip()
                
                logger.debug(f"找到时间戳: {time_matches}, 歌词文本: '{text}'")
                
                # 为每个时间戳创建歌词行
                for time_str in time_matches:
                    time_ms = LRCParser.parse_time(time_str)
                    if text or time_ms == 0:  # 允许空歌词（间奏等）
                        lyrics.append(LyricLine(time_ms, text))
                        logger.info(f"添加歌词行: {time_str} -> {time_ms}ms -> '{text}'")
            else:
                logger.debug(f"未匹配到时间戳格式的行: {line}")
        
        # 按时间排序
        lyrics.sort()
        
        logger.info(f"解析LRC完成: {len(lyrics)}行歌词, 元数据: {metadata}")
        if lyrics:
            logger.info(f"第一行歌词: {lyrics[0]}")
            logger.info(f"最后一行歌词: {lyrics[-1]}")
        
        return lyrics, metadata

class LRCManager:
    """LRC歌词管理器 - 线程安全版本，不依赖Qt"""
    
    def __init__(self, subtitle_manager=None):
        self.subtitle_manager = subtitle_manager
        self.lyrics: List[LyricLine] = []
        self.metadata: Dict[str, str] = {}
        self.current_index = 0
        self.start_time = 0
        self.is_playing = False
        self.is_paused = False
        self.pause_time = 0
        
        # 使用Python线程替代Qt定时器
        self._timer_thread = None
        self._stop_timer = False
        self.timer_interval = 0.05  # 50ms检查一次
        
    def load_lrc_content(self, lrc_content: str) -> bool:
        """加载LRC歌词内容
        
        Args:
            lrc_content: LRC文件内容
            
        Returns:
            bool: 是否加载成功
        """
        try:
            self.lyrics, self.metadata = LRCParser.parse_lrc_content(lrc_content)
            self.current_index = 0
            
            if self.lyrics:
                logger.info(f"加载LRC歌词成功: {len(self.lyrics)}行")
                logger.info(f"歌词元数据: {self.metadata}")
                return True
            else:
                logger.warning("LRC歌词内容为空")
                return False
                
        except Exception as e:
            logger.error(f"加载LRC歌词失败: {e}")
            return False
    
    def start_playback(self):
        """开始歌词播放"""
        if not self.lyrics:
            logger.warning("没有歌词数据，无法开始播放")
            return
        
        logger.info("开始LRC歌词播放")
        self.start_time = time.time() * 1000  # 转换为毫秒
        self.current_index = 0
        self.is_playing = True
        self.is_paused = False
        self._stop_timer = False
        
        # 启动定时器线程
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
        
        # 显示第一行歌词（如果时间为0）
        if self.lyrics and self.lyrics[0].time_ms == 0:
            self._display_lyric(self.lyrics[0].text)
    
    def pause_playback(self):
        """暂停歌词播放"""
        if self.is_playing and not self.is_paused:
            logger.info("暂停LRC歌词播放")
            self.is_paused = True
            self.pause_time = time.time() * 1000
    
    def resume_playback(self):
        """恢复歌词播放"""
        if self.is_playing and self.is_paused:
            logger.info("恢复LRC歌词播放")
            # 调整开始时间，补偿暂停的时间
            pause_duration = time.time() * 1000 - self.pause_time
            self.start_time += pause_duration
            self.is_paused = False
    
    def stop_playback(self):
        """停止歌词播放"""
        logger.info("停止LRC歌词播放")
        self.is_playing = False
        self.is_paused = False
        self._stop_timer = True
        self.current_index = 0
        
        # 等待定时器线程结束（但不在当前线程中等待自己）
        if self._timer_thread and self._timer_thread.is_alive():
            # 检查是否是当前线程试图join自己
            current_thread = threading.current_thread()
            if self._timer_thread != current_thread:
                self._timer_thread.join(timeout=1.0)
            else:
                # 如果是当前线程，只设置停止标志，不等待
                logger.debug("检测到当前线程试图join自己，跳过等待")
        
        # 清空显示
        self._display_lyric("")
    
    def seek_to_time(self, time_ms: int):
        """跳转到指定时间
        
        Args:
            time_ms: 目标时间（毫秒）
        """
        if not self.lyrics:
            return
        
        # 调整开始时间
        current_time = time.time() * 1000
        self.start_time = current_time - time_ms
        
        # 找到对应的歌词索引
        for i, lyric in enumerate(self.lyrics):
            if lyric.time_ms > time_ms:
                self.current_index = max(0, i - 1)
                break
        else:
            self.current_index = len(self.lyrics) - 1
        
        # 显示当前歌词
        if 0 <= self.current_index < len(self.lyrics):
            self._display_lyric(self.lyrics[self.current_index].text)
        
        logger.info(f"跳转到时间: {time_ms}ms, 歌词索引: {self.current_index}")
    
    def _timer_loop(self):
        """定时器循环线程"""
        while not self._stop_timer and self.is_playing:
            if not self.is_paused:
                self._check_lyric_timing()
            time.sleep(self.timer_interval)
    
    def _check_lyric_timing(self):
        """检查歌词显示时机"""
        if not self.is_playing or self.is_paused or not self.lyrics:
            return
        
        current_time = time.time() * 1000
        elapsed_time = current_time - self.start_time
        
        # 每10秒输出一次时间信息用于调试
        if int(elapsed_time / 1000) % 10 == 0 and (elapsed_time % 1000) < 100:
            logger.info(f"LRC播放进度: {self._format_time(int(elapsed_time))}, 当前歌词索引: {self.current_index}/{len(self.lyrics)}")
        
        # 检查是否需要显示下一行歌词
        displayed_lyrics = False
        while (self.current_index < len(self.lyrics) and 
               self.lyrics[self.current_index].time_ms <= elapsed_time):
            
            lyric = self.lyrics[self.current_index]
            self._display_lyric(lyric.text)
            
            logger.info(f"显示歌词 [{self._format_time(lyric.time_ms)}]: {lyric.text}")
            displayed_lyrics = True
            
            self.current_index += 1
        
        # 检查是否播放完成
        if self.current_index >= len(self.lyrics):
            # 检查是否已经过了最后一行歌词的显示时间
            last_lyric_time = self.lyrics[-1].time_ms
            if elapsed_time > last_lyric_time + 3000:  # 最后一行歌词显示3秒后结束
                logger.info("LRC歌词播放已完成")
                # 不在定时器线程中调用stop_playback，而是设置停止标志
                self.is_playing = False
                self._stop_timer = True
                self._display_lyric("")  # 清空显示
    
    def _display_lyric(self, text: str):
        """显示歌词文本"""
        # 如果有字幕管理器，同时更新字幕显示
        if self.subtitle_manager:
            if text.strip():
                # 显示歌词，使用完整显示而不是流式显示
                self.subtitle_manager.add_text(text, stream=False)
            else:
                # 空歌词时清空显示
                self.subtitle_manager.clear_text()
    
    def _format_time(self, time_ms: int) -> str:
        """格式化时间显示
        
        Args:
            time_ms: 毫秒数
            
        Returns:
            str: 格式化的时间字符串
        """
        total_seconds = time_ms / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int(time_ms % 1000)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
    def get_current_lyric(self) -> Optional[str]:
        """获取当前歌词
        
        Returns:
            Optional[str]: 当前歌词文本，如果没有则返回None
        """
        if (0 <= self.current_index < len(self.lyrics)):
            return self.lyrics[self.current_index].text
        return None
    
    def get_next_lyric(self) -> Optional[str]:
        """获取下一行歌词
        
        Returns:
            Optional[str]: 下一行歌词文本，如果没有则返回None
        """
        next_index = self.current_index + 1
        if 0 <= next_index < len(self.lyrics):
            return self.lyrics[next_index].text
        return None
    
    def get_lyric_info(self) -> Dict[str, Any]:
        """获取歌词信息
        
        Returns:
            Dict[str, Any]: 歌词信息
        """
        current_time = 0
        if self.is_playing and not self.is_paused:
            current_time = time.time() * 1000 - self.start_time
        
        return {
            "total_lines": len(self.lyrics),
            "current_index": self.current_index,
            "current_time_ms": int(current_time),
            "current_lyric": self.get_current_lyric(),
            "next_lyric": self.get_next_lyric(),
            "metadata": self.metadata,
            "is_playing": self.is_playing,
            "is_paused": self.is_paused
        }

def test_lrc_parser():
    """测试LRC解析器"""
    print("测试LRC解析器...")
    
    # 测试LRC内容
    test_lrc = """[ar:测试歌手]
[ti:测试歌曲]
[al:测试专辑]
[by:LRC Maker]

[00:00.00]这是开头
[00:05.50]第一句歌词
[00:10.30]第二句歌词
[00:15.80][00:45.20]重复的歌词
[00:20.10]第三句歌词
[00:25.60]
[00:30.40]第四句歌词
[00:35.90]这是结尾"""
    
    lyrics, metadata = LRCParser.parse_lrc_content(test_lrc)
    
    print(f"解析结果:")
    print(f"元数据: {metadata}")
    print(f"歌词行数: {len(lyrics)}")
    
    for lyric in lyrics:
        print(f"  {lyric}")

if __name__ == "__main__":
    test_lrc_parser()
