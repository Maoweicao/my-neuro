#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事件总线(EventBus)模块测试脚本 - 完全异步化版本
"""

import sys
import os
import asyncio
import logging
import time

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_event_bus")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入事件总线
from core.event_bus import EventBus

async def test_basic_event_handling():
    """测试基本事件处理功能"""
    event_bus = EventBus()
    
    # 测试数据
    received_events = []
    event_received = asyncio.Event()  # 异步事件标志
    
    # 异步回调函数
    async def on_test_event(data):
        logger.info(f"收到测试事件: {data}")
        received_events.append(data)
        event_received.set()  # 设置事件标志
    
    # 订阅事件
    await event_bus.subscribe("test_event", on_test_event)
    
    # 发布事件
    logger.info("发布普通事件")
    await event_bus.publish("test_event", {"message": "Hello, Async EventBus!"})
    
    # 等待事件处理完成
    try:
        await asyncio.wait_for(event_received.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        logger.error("超时：没有收到测试事件")
        assert False, "事件未在指定时间内处理"
    
    # 验证事件是否被接收
    assert len(received_events) == 1, f"应该收到1个事件，实际收到{len(received_events)}个"
    assert received_events[0]["message"] == "Hello, Async EventBus!", "事件数据不匹配"
    
    # 关闭事件总线
    await event_bus.shutdown()
    logger.info("基本事件测试完成")

async def test_unsubscribe():
    """测试取消订阅功能"""
    event_bus = EventBus()
    
    received_events = []
    
    async def on_test_event(data):
        received_events.append(data)
    
    # 订阅事件
    await event_bus.subscribe("test_event", on_test_event)
    
    # 发布事件并验证
    await event_bus.publish("test_event", {"id": 1})
    await asyncio.sleep(0.1)  # 给事件处理时间
    assert len(received_events) == 1, "订阅后应收到事件"
    
    # 取消订阅
    await event_bus.unsubscribe("test_event", on_test_event)
    
    # 再次发布事件
    await event_bus.publish("test_event", {"id": 2})
    await asyncio.sleep(0.1)  # 给事件处理时间
    
    # 验证只收到第一个事件
    assert len(received_events) == 1, "取消订阅后不应再收到事件"
    assert received_events[0]["id"] == 1, "事件数据错误"
    
    await event_bus.shutdown()
    logger.info("取消订阅测试完成")

async def test_sync_callback():
    """测试同步回调处理"""
    event_bus = EventBus()
    
    received_events = []
    event_received = asyncio.Event()
    
    # 获取主事件循环
    main_loop = asyncio.get_event_loop()
    
    # 同步回调函数 - 使用全局事件循环
    def sync_callback(data):
        logger.info(f"同步回调收到事件: {data}")
        received_events.append(data)
        # 使用主事件循环的 call_soon_threadsafe 方法
        main_loop.call_soon_threadsafe(event_received.set)
    
    # 订阅事件
    await event_bus.subscribe("sync_event", sync_callback)
    
    # 发布事件
    await event_bus.publish("sync_event", {"type": "sync"})
    
    # 等待事件处理
    try:
        await asyncio.wait_for(event_received.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        assert False, "同步回调未在指定时间内完成"
    
    assert len(received_events) == 1, "同步回调未正确执行"
    
    await event_bus.shutdown()
    logger.info("同步回调测试完成")

async def test_async_callback():
    """测试异步回调处理"""
    event_bus = EventBus()
    
    received_events = []
    event_received = asyncio.Event()
    
    # 异步回调函数
    async def async_callback(data):
        logger.info(f"异步回调开始处理: {data}")
        await asyncio.sleep(0.2)  # 模拟异步操作
        received_events.append(data)
        event_received.set()
        logger.info("异步回调处理完成")
    
    # 订阅事件
    await event_bus.subscribe("async_event", async_callback)
    
    # 发布事件
    start_time = time.monotonic()
    await event_bus.publish("async_event", {"type": "async"})
    publish_duration = time.monotonic() - start_time
    
    # 验证发布操作没有被阻塞
    assert publish_duration < 0.1, f"发布操作应快速返回，实际耗时{publish_duration:.4f}s"
    
    # 等待事件处理
    try:
        await asyncio.wait_for(event_received.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        assert False, "异步回调未在指定时间内完成"
    
    assert len(received_events) == 1, "异步回调未正确执行"
    
    await event_bus.shutdown()
    logger.info("异步回调测试完成")

async def test_multiple_subscribers():
    """测试多个订阅者 - 修复协程未等待问题"""
    event_bus = EventBus()
    
    results = {"sub1": 0, "sub2": 0, "sub3": 0}
    all_done = asyncio.Event()
    done_count = 0
    
    async def increment_counter(sub_id, data):
        results[sub_id] += 1
        nonlocal done_count
        done_count += 1
        if done_count == 3:
            all_done.set()
    
    # 定义明确的异步回调函数
    async def callback1(data):
        await increment_counter("sub1", data)
    
    async def callback2(data):
        await increment_counter("sub2", data)
    
    async def callback3(data):
        await increment_counter("sub3", data)
    
    # 订阅事件
    await event_bus.subscribe("multi_event", callback1)
    await event_bus.subscribe("multi_event", callback2)
    await event_bus.subscribe("multi_event", callback3)
    
    # 发布事件
    await event_bus.publish("multi_event", {"value": 42})
    
    # 等待所有回调完成
    try:
        await asyncio.wait_for(all_done.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        assert False, "未所有订阅者未在指定时间内完成"
    
    # 验证所有订阅者都收到了事件
    assert results["sub1"] == 1, "订阅者1未收到事件"
    assert results["sub2"] == 1, "订阅者2未收到事件"
    assert results["sub3"] == 1, "订阅者3未收到事件"
    
    await event_bus.shutdown()
    logger.info("多订阅者测试完成")

async def test_shutdown_behavior():
    """测试关闭行为"""
    event_bus = EventBus()
    
    shutdown_completed = False
    event_received_during_shutdown = asyncio.Event()
    
    async def test_callback(data):
        # 如果已开始关闭，记录事件接收情况
        if shutdown_completed:
            logger.warning("在关闭后收到事件")
            event_received_during_shutdown.set()
    
    # 订阅事件
    await event_bus.subscribe("shutdown_test", test_callback)
    
    # 正常发布事件
    await event_bus.publish("shutdown_test", {"status": "normal"})
    await asyncio.sleep(0.1)  # 给事件处理时间
    
    # 开始关闭
    shutdown_completed = True
    shutdown_task = asyncio.create_task(event_bus.shutdown())
    
    # 尝试在关闭过程中发布事件
    await event_bus.publish("shutdown_test", {"status": "during_shutdown"})
    
    # 等待关闭完成
    await shutdown_task
    
    # 确保关闭后没有处理事件
    assert not event_received_during_shutdown.is_set(), "关闭后不应处理新事件"
    
    logger.info("关闭行为测试完成")

async def run_all_tests():
    """运行所有测试"""
    tests = [
        test_basic_event_handling,
        test_unsubscribe,
        test_sync_callback,
        test_async_callback,
        test_multiple_subscribers,
        test_shutdown_behavior
    ]
    
    for test in tests:
        logger.info(f"开始测试: {test.__name__}")
        try:
            await test()
            logger.info(f"测试通过: {test.__name__}")
        except Exception as e:
            logger.error(f"测试失败: {test.__name__} - {e}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(run_all_tests())