// synchronized-emotion-motion-mapper.js - 与TTS系统同步的情绪动作映射器
class EmotionMotionMapper {
    constructor(model) {
        this.model = model;
        this.currentMotionGroup = "TapBody";  // 使用TapBody组，包含所有动作
        
        // 情绪到动作索引的映射
        this.emotionMap = {
            '开心高': 0,   // 动作0：左右歪头，结尾闭眼笑嘻嘻（打量开心，兴奋度3）
            '开心低': 1,   // 动作1：双手对称摇动，头左右摇动（开心，兴奋度1）
            '愧疚': 2,     // 动作2：皱眉，双手放背后，扭捏表情（愧疚情绪）
            '开心中': 3,   // 动作3：摇晃身体，张开双臂，笑脸（开心，兴奋度2）
            '俏皮': 4,     // 动作4：手臂抬至胸前，由中间向外展开，结尾笑脸（俏皮，可爱）
            '惊讶': 5,     // 动作5：双手放到背后，身体一抖，惊愕状（惊讶、困惑）
            '兴奋': 6,     // 动作6：双手抬至胸前快速展开，结尾笑脸（高兴兴奋）
            '赌气': 7,     // 动作7：抬眉毛，然后半闭眼赌气（赌气、可爱）
            '悲伤': 8      // 动作8：双手放置背后，皱眉，难受（悲伤）
        };
        
        // 动作描述，用于日志
        this.motionDescriptions = [
            "开心兴奋(0号): 左右歪头，结尾闭眼笑嘻嘻",
            "轻微开心(1号): 双手对称摇动，头左右摇动",
            "愧疚(2号): 皱眉，双手放背后，扭捏表情",
            "中等开心(3号): 摇晃身体，张开双臂，笑脸", 
            "俏皮可爱(4号): 手臂抬至胸前，由中间向外展开",
            "惊讶(5号): 双手放到背后，身体一抖，惊愕状",
            "高度兴奋(6号): 双手抬至胸前，由中间向外展开，更快速",
            "赌气(7号): 抬眉毛，然后半闭眼赌气",
            "悲伤(8号): 双手放置背后，皱眉，难受"
        ];
        
        // 动作播放状态
        this.isPlayingMotion = false;
        
        // 动作之间的间隔时间（毫秒）
        this.motionInterval = 2000; // 默认2秒间隔
    }

    // 解析文本，提取所有情绪标签和位置信息
    parseEmotionTagsWithPosition(text) {
        // 使用正则表达式匹配所有情绪标签 《xxx》
        const pattern = /<([^>]+)>/g;
        const emotions = [];
        let match;
        
        while ((match = pattern.exec(text)) !== null) {
            emotions.push({
                emotion: match[1],
                startIndex: match.index,
                endIndex: match.index + match[0].length,
                fullTag: match[0]
            });
        }
        
        return emotions;
    }

    // 预处理文本，为TTS系统做准备
    // 返回: { text: 去除情绪标签的纯文本, emotionMarkers: 带位置信息的情绪标记 }
    prepareTextForTTS(text) {
        // 提取情绪标签和位置
        const emotionTags = this.parseEmotionTagsWithPosition(text);
        
        // 如果没有情绪标签，直接返回原文本
        if (emotionTags.length === 0) {
            return { 
                text: text, 
                emotionMarkers: [] 
            };
        }
        
        // 创建纯文本版本（移除所有情绪标签）
        let purifiedText = text;
        // 从后向前处理，避免位置偏移问题
        for (let i = emotionTags.length - 1; i >= 0; i--) {
            const tag = emotionTags[i];
            purifiedText = purifiedText.substring(0, tag.startIndex) + 
                           purifiedText.substring(tag.endIndex);
        }
        
        // 创建情绪标记数组，转换为基于字符位置的标记
        const emotionMarkers = [];
        let offset = 0;
        
        for (const tag of emotionTags) {
            // 计算标签位置，考虑前面移除的标签导致的偏移
            const adjustedPosition = tag.startIndex - offset;
            
            // 标签长度会影响后续标签的位置计算
            offset += tag.endIndex - tag.startIndex;
            
            // 检查情绪是否有效
            const motionIndex = this.emotionMap[tag.emotion];
            if (motionIndex !== undefined) {
                emotionMarkers.push({
                    position: adjustedPosition,
                    emotion: tag.emotion,
                    motionIndex: motionIndex
                });
            }
        }
        
        return {
            text: purifiedText,
            emotionMarkers: emotionMarkers
        };
    }
    
    // 根据文字显示位置触发情绪动作
    // position: 当前字幕显示到的字符位置
    // textLength: 总字符长度
    triggerEmotionByTextPosition(position, textLength, emotionMarkers) {
        if (!emotionMarkers || emotionMarkers.length === 0) return;
        
        // 找到当前位置应该触发的情绪
        for (const marker of emotionMarkers) {
            // 当字幕位置刚好到达或略微超过情绪标记位置时触发
            if (position >= marker.position && 
                position <= marker.position + 2) { // 添加小缓冲区，避免可能的同步误差
                
                // 触发对应的动作
                const motionIndex = marker.motionIndex;
                console.log(`触发情绪: ${marker.emotion}, 动作: ${motionIndex} - ${this.motionDescriptions[motionIndex]}`);
                this.playMotion(motionIndex);
                
                // 移除已处理的标记，避免重复触发
                const index = emotionMarkers.indexOf(marker);
                if (index > -1) {
                    emotionMarkers.splice(index, 1);
                }
                
                break; // 一次只处理一个情绪标记
            }
        }
    }

    // 为了向后兼容，保留原有接口，但修改内部实现
    triggerMotionByEmotion(text) {
        // 提取第一个情绪标签
        const match = text.match(/<([^>]+)>/);
        if (match && match[1]) {
            const emotion = match[1];
            const motionIndex = this.emotionMap[emotion];
            
            if (motionIndex !== undefined) {
                console.log(`检测到情绪: ${emotion}, 触发动作: ${motionIndex} - ${this.motionDescriptions[motionIndex]}`);
                this.playMotion(motionIndex);
            }
        }
        
        // 移除所有情绪标签后返回纯文本
        return text.replace(/<[^>]+>/g, '').trim();
    }
    
    // 播放指定索引的动作
    playMotion(index) {
        if (!this.model) return;
        
        try {
            // 获取动作配置
            const motionDefinitions = this.model.internalModel.settings.motions[this.currentMotionGroup];
            if (!motionDefinitions || motionDefinitions.length === 0) {
                console.error('没有找到动作定义');
                return;
            }
            
            // 确保索引在有效范围内
            const motionIndex = index % motionDefinitions.length;
            
            // 停止当前动作
            if (this.model.internalModel && this.model.internalModel.motionManager) {
                this.model.internalModel.motionManager.stopAllMotions();
            }
            
            // 播放新动作
            this.model.motion(this.currentMotionGroup, motionIndex);
            
            // 获取当前动作文件名称进行打印
            const currentMotionFile = motionDefinitions[motionIndex].File;
            console.log(`播放动作: ${currentMotionFile} (索引: ${motionIndex})`);
        } catch (error) {
            console.error('播放动作失败:', error);
        }
    }
    
    // 播放默认动作
    playDefaultMotion() {
        // 播放默认的Idle动作
        try {
            this.model.motion("Idle", 0);
            console.log("播放默认动作: Idle");
        } catch (error) {
            console.error('播放默认动作失败:', error);
        }
    }
}

module.exports = { EmotionMotionMapper };