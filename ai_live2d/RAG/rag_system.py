"""
RAG系统 - 负责知识库及记忆检索
"""
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"  # 禁用网络连接
os.environ["HF_DATASETS_OFFLINE"] = "1"  # 禁用数据集网络连接
import aiohttp
import logging
from typing import List

logger = logging.getLogger("rag_system")

class RagSystem:
    """RAG系统, 负用于知识库及记忆的处理及检索"""

    def __init__(self, config:dict, event_bus=None):
        """初始化RAG系统
        
        Args:
            config: 配置信息，包含RAG相关配置
            event_bus: 事件总线，用于发布事件
        """
        self.config = config
        self.event_bus = event_bus

        # 从配置信息中获取RAG相关配置
        self.url = self.config.get('rag', {}).get('rag_url', 'http://127.0.0.1:6600/rag')

        if os.path.exists('RAG/counts'):
            with open('RAG/counts', 'r', encoding='utf-8') as count:
                self.counts = int(count.read())
        else:
            with open('RAG/counts', 'w', encoding='utf-8') as count:
                count.write('0')
                self.counts = 0
        
        # 已记录的对话条数
        self.records = 0

        # 创建持久化HTTP连接池
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(),
            connector=aiohttp.TCPConnector(limit_per_host=4)
        )

    async def start(self):
        """开启RAG API"""
        if len(self.spilit_into_chunks('chat_log.txt')) > self.counts:
            await self.update_database('chat_log.txt')
        
    def spilit_into_chunks(self, doc_file: str) -> List[str]:
        """分片 - 对文本进行切分"""
        with open(doc_file, 'r', encoding='utf-8') as file:
            content = file.read()
        return [chunk for chunk in content.split('\n\n') if chunk]
    
    async def get_output(self, query: str):
        """生成 - 获得输出"""
        try:
            # 使用aiohttp进行异步请求
            async with self.session.post(
                self.url+'/output', 
                json={'query': query}, 
                headers={"Content-Type": "application/json"}
                    ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"RAG服务器错误: {response.status}, {error_text}")
                
                reranked_chunks = await response.json()

            await self.event_bus.publish("get_rag_output", {'user_input': query, "rag_output": '\n'.join(reranked_chunks)})
        except Exception as e:
            logger.error(f"RAG输出错误:{e}")
            await self.event_bus.publish("get_rag_output", {'user_input': query, "rag_output": 'ERROR检索错误'})

    async def update_database(self, doc_file: str):
        """更新向量数据库"""
        try:
            chunks = self.spilit_into_chunks(doc_file)

            # 使用aiohttp进行异步请求
            async with self.session.post(
                self.url+'/update', 
                json={'chunks': chunks, 'counts': self.counts}, 
                headers={"Content-Type": "application/json"}
                    ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"RAG服务器错误: {response.status}, {error_text}")
                
                self.counts += await response.json()
                with open('RAG/counts', 'w', encoding='utf-8') as count:
                    count.write(str(self.counts))

        except Exception as e:
            logger.error(f"RAG数据更新错误:{e}")
            return