#!/usr/bin/env python3
"""
豆包语音服务WebSocket协议处理模块
支持TTS和ASR的协议解析
"""
import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional


class MsgType(IntEnum):
    """消息类型枚举"""
    CLIENT_REQUEST = 0x1
    SERVER_RESPONSE = 0x2
    AudioOnlyServer = 0xb
    FrontEndResultServer = 0x3


@dataclass
class Message:
    """WebSocket消息结构"""
    type: MsgType
    sequence: int
    payload: bytes


async def full_client_request(websocket, payload: bytes) -> None:
    """发送完整的客户端请求"""
    # 构建消息头 (16字节)
    # 4字节: 消息类型 (CLIENT_REQUEST = 1)
    # 4字节: 序列号 (1)  
    # 4字节: payload长度
    # 4字节: 保留字段 (0)
    
    msg_type = MsgType.CLIENT_REQUEST
    sequence = 1
    payload_size = len(payload)
    reserved = 0
    
    header = struct.pack('<IIII', msg_type, sequence, payload_size, reserved)
    
    # 发送头部 + 数据
    await websocket.send(header + payload)


async def receive_message(websocket) -> Message:
    """接收WebSocket消息"""
    # 读取消息头 (16字节)
    header_data = await websocket.recv()
    
    if len(header_data) < 16:
        # 如果收到的数据少于16字节，说明包含了头部和数据
        # 需要分离头部和数据
        if len(header_data) >= 16:
            header = header_data[:16]
            payload = header_data[16:]
        else:
            raise ValueError(f"接收到的数据长度不足: {len(header_data)} bytes")
    else:
        # 标准情况：先收到16字节头部
        header = header_data[:16] if len(header_data) >= 16 else header_data
        payload = header_data[16:] if len(header_data) > 16 else b''
    
    # 解析头部
    msg_type, sequence, payload_size, reserved = struct.unpack('<IIII', header)
    
    # 如果payload不完整，继续接收
    while len(payload) < payload_size:
        additional_data = await websocket.recv()
        payload += additional_data
    
    # 只取需要的payload长度
    payload = payload[:payload_size]
    
    return Message(
        type=MsgType(msg_type),
        sequence=sequence,
        payload=payload
    )


def create_audio_packet(audio_data: bytes, sequence: int = 1, is_final: bool = False) -> bytes:
    """创建音频数据包"""
    msg_type = MsgType.CLIENT_REQUEST
    payload_size = len(audio_data)
    reserved = 0
    
    # 如果是最后一个包，序列号设为负数
    if is_final:
        sequence = -sequence
    
    header = struct.pack('<IIII', msg_type, sequence, payload_size, reserved)
    return header + audio_data


def parse_audio_response(data: bytes) -> Optional[Message]:
    """解析音频响应数据"""
    if len(data) < 16:
        return None
    
    header = data[:16]
    payload = data[16:]
    
    msg_type, sequence, payload_size, reserved = struct.unpack('<IIII', header)
    
    # 确保payload长度正确
    if len(payload) < payload_size:
        return None
    
    payload = payload[:payload_size]
    
    return Message(
        type=MsgType(msg_type),
        sequence=sequence,
        payload=payload
    )
