import numpy as np
import struct
import time

class WavHandler:
    def __init__(self):
        # 每个通道的采样帧数
        self.numFrames: int = 0
        # 采样率，帧/秒
        self.sampleRate: int = 0
        self.sampleWidth: int = 0
        # 数据
        self.pcmData: np.ndarray = None
        # 已经读取的帧数
        self.lastOffset: int = 0
        # 当前rms值
        self.currentRms: float = 0
        # 开始读取的时间
        self.startTime: float = -1
        # 原始音频字节数据缓存
        self.rawBytes: bytes = b''

    def Start(self, data:dict) -> None:
        self.ReleasePcmData()
        try:
            self.numFrames = data.get('num_frames')
            self.sampleRate = data.get('framerate')
            self.sampleWidth = data.get('sample_width')
            self.numChannels = data.get('channels')
            self.rawBytes = data.get('frames')
            # 双声道 / 单声道
            self.pcmData = data.get('pcm_data')
            # 拆分通道
            if self.numChannels > 1:
                self.pcmData = self.pcmData.T

            self.startTime = time.time()
            self.lastOffset = 0

        except Exception as e:
            self.ReleasePcmData()

    def ReleasePcmData(self):
        if self.pcmData is not None:
            del self.pcmData
            self.pcmData = None
        self.rawBytes = b''  # 清空字节缓存

    def GetRms(self) -> float:
        """
        获取当前音频响度
        """
        return self.currentRms
    
    def calculate_rms(self, data: bytes) -> float:
        """计算RMS音量标准--肥波佬提供"""
        length = len(data) / 2
        shorts = struct.unpack("%dh" % length, data)
        sum_squares = 0.0
        for sample in shorts:
            n = sample * (1.0 / 32768)
            sum_squares += n * n
        rms = np.sqrt(sum_squares / length)
        return rms

    def Update(self) -> bool:
        """
        更新位置
        """
        # 数据未加载或者数据已经读取完毕
        if not self.rawBytes or self.lastOffset >= self.numFrames:
            return False

        currentTime = time.time() - self.startTime
        currentOffset = int(currentTime * self.sampleRate)

        # 时间太短
        if currentOffset <= self.lastOffset:
            return True

        currentOffset = min(currentOffset, self.numFrames)

        # 计算当前片段对应的字节位置
        bytes_per_frame = self.sampleWidth * self.numChannels
        start_byte = self.lastOffset * bytes_per_frame
        end_byte = currentOffset * bytes_per_frame
        
        # 提取当前音频片段的字节数据
        audio_bytes = self.rawBytes[start_byte:end_byte]
        
        # 使用提供的RMS函数计算响度
        if audio_bytes:
            self.currentRms = min(1.0, self.calculate_rms(audio_bytes) * 3.0)
        else:
            self.currentRms = 0.0

        self.lastOffset = currentOffset
        return True