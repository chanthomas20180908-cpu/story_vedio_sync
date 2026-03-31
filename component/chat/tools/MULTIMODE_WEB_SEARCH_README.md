# 多模式网络查询功能使用说明

## 概述

Agent现在支持**四种网络查询模式**，可以智能推荐不同场景下的最佳网站：

| 模式 | 适用场景 | 网站类型 | 数量 |
|------|---------|---------|------|
| **technical** | 技术调研 | GitHub、HuggingFace、arXiv等 | 35个平台 + 4个搜索引擎 |
| **product** | 产品学习 | 人人都是产品经理、36氪、知乎等 | 22个平台 + 4个搜索引擎 |
| **ai_news** | AI资讯 | 机器之心、量子位、Papers with Code等 | 25个平台 + 4个搜索引擎 |
| **comprehensive** | 综合查询 | 所有类型网站 | 82个平台 + 12个搜索引擎 |

## 功能特点

✅ **智能匹配**：自动根据关键词推荐最相关的网站  
✅ **多场景支持**：技术、产品、资讯一应俱全  
✅ **精确+模糊**：支持精确匹配和模糊搜索  
✅ **向后兼容**：保留旧API，无缝迁移  
✅ **可扩展**：配置化管理，易于添加新网站

## 使用方式

### 方式1：AI Agent 自动调用

Agent会根据用户问题**自动选择**合适的模式：

```python
# 用户问题示例
"帮我查一下Qwen3的技术文档"           # → AI选择 mode=technical
"我想学习用户增长的方法论"            # → AI选择 mode=product  
"最近有什么AI行业新闻"                # → AI选择 mode=ai_news
"全面调研一下AI Agent"                # → AI选择 mode=comprehensive
```

### 方式2：编程调用

```python
from component.chat.tools.web_tools import WebTools

web_tools = WebTools()

# 技术查询
result = web_tools.suggest_url("qwen3", mode="technical")
print(result['suggested_url'])  # https://github.com/QwenLM/Qwen

# 产品查询
result = web_tools.suggest_url("用户增长", mode="product")
print(result['suggested_url'])  # https://www.woshipm.com/tag/%E7%94%A8%E6%88%B7%E5%A2%9E%E9%95%BF

# AI资讯查询
result = web_tools.suggest_url("机器之心", mode="ai_news")
print(result['suggested_url'])  # https://www.jiqizhixin.com

# 综合查询
result = web_tools.suggest_url("AI Agent", mode="comprehensive")
print(result['all_suggestions'])  # 返回12个推荐链接
```

### 方式3：Function Calling（Agent内部）

```json
{
  "function": "suggest_url",
  "arguments": {
    "keyword": "用户增长",
    "mode": "product"
  }
}
```

## 使用场景示例

### 场景1：技术调研

**用户需求**：了解某个开源模型的技术实现

```
用户：帮我查一下 Qwen3 的技术文档和代码仓库
AI：  [调用] suggest_url("qwen3", mode="technical")
     → 推荐：https://github.com/QwenLM/Qwen
     
用户：Stable Diffusion 的最新版本有什么改进
AI：  [调用] suggest_url("stable-diffusion", mode="technical")
     → 推荐：https://github.com/Stability-AI/stablediffusion
```

**覆盖平台**：
- AI模型：Qwen、LLaMA、DeepSeek、ChatGLM等
- 图像模型：Stable Diffusion、FLUX、DALL-E等
- 视频生成：Sora、Runway、Pika
- 语音模型：Whisper、CosyVoice、Bark
- 框架工具：LangChain、Transformers、PyTorch等

### 场景2：产品学习

**用户需求**：学习产品方法论和案例

```
用户：我想学习用户增长的方法
AI：  [调用] suggest_url("用户增长", mode="product")
     → 推荐：https://www.woshipm.com/tag/%E7%94%A8%E6%88%B7%E5%A2%9E%E9%95%BF
     
用户：有没有关于MVP的产品案例
AI：  [调用] suggest_url("MVP方法论", mode="product")
     → 推荐搜索：
       1. https://www.woshipm.com/search?keyword=MVP方法论
       2. https://36kr.com/search?keyword=MVP方法论
       3. https://www.zhihu.com/search?q=MVP方法论
```

**覆盖平台**：
- 产品社区：人人都是产品经理、PMCaff、产品壹佰
- 科技媒体：36氪、虎嗅、少数派、爱范儿
- 数据分析：神策数据、GrowingIO
- 设计平台：站酷、优设、UI中国
- 知识平台：知乎、增长黑客

### 场景3：AI资讯追踪

**用户需求**：关注AI行业最新动态

```
用户：最近有什么AI行业新闻
AI：  [调用] suggest_url("AI新闻", mode="ai_news")
     → 推荐：https://www.jiqizhixin.com
     
用户：大模型最新研究进展
AI：  [调用] suggest_url("大模型最新进展", mode="ai_news")
     → 推荐搜索：
       1. https://www.jiqizhixin.com/search?keyword=大模型最新进展
       2. https://www.qbitai.com/?s=大模型最新进展
       3. https://paperswithcode.com/search?q=大模型最新进展
```

**覆盖平台**：
- 中文媒体：机器之心、量子位、新智元、雷峰网AI、智东西
- 英文媒体：OpenAI Blog、Google AI Blog、DeepMind Blog
- 学术平台：arXiv AI、Papers with Code、HuggingFace Blog
- 行业报告：AI指数、行业研究报告

### 场景4：综合调研

**用户需求**：全面了解某个主题

```
用户：全面调研一下 AI Agent 的技术实现和产品应用
AI：  [调用] suggest_url("AI Agent", mode="comprehensive")
     → 返回12个推荐（包含技术、产品、资讯所有类型）
     
     [然后调用] fetch_url 分别访问推荐的网站
     [最后] 综合分析并生成报告
```

## 匹配规则

### 1. 精确匹配

关键词与预设平台完全匹配（不区分大小写）

```python
"qwen3" → https://github.com/QwenLM/Qwen              # 技术模式
"用户增长" → https://www.woshipm.com/tag/...          # 产品模式
"机器之心" → https://www.jiqizhixin.com                # AI资讯模式
```

### 2. 模糊匹配

关键词包含在平台名称中，或平台名称包含在关键词中

```python
"stable diffusion" → 匹配到 "stable-diffusion"
"产品" → 匹配到 "产品经理" 
"AI" → 匹配到 "ai资讯"
```

### 3. 搜索建议

无法匹配时，返回该模式下的搜索引擎链接

```python
# 技术模式
"AI Agent实现" → [
    "https://github.com/search?q=AI Agent实现",
    "https://huggingface.co/models?search=AI Agent实现",
    "https://arxiv.org/search/?query=AI Agent实现",
    "https://paperswithcode.com/search?q_meta=AI Agent实现"
]

# 产品模式  
"MVP方法论" → [
    "https://www.woshipm.com/search?keyword=MVP方法论",
    "https://36kr.com/search?keyword=MVP方法论",
    "https://www.zhihu.com/search?q=MVP方法论",
    "https://coffee.pmcaff.com/search?q=MVP方法论"
]

# AI资讯模式
"大模型" → [
    "https://www.jiqizhixin.com/search?keyword=大模型",
    "https://www.qbitai.com/?s=大模型",
    "https://www.leiphone.com/search?keyword=大模型",
    "https://paperswithcode.com/search?q=大模型"
]
```

## 返回结果格式

```python
{
    "success": True,
    "keyword": "qwen3",
    "mode": "technical",
    "mode_description": "技术文档和开源项目（GitHub、HuggingFace、arXiv等）",
    "suggested_url": "https://github.com/QwenLM/Qwen",
    "match_type": "exact",  # exact/fuzzy/search
    "source": "预设平台映射（技术文档和开源项目...）",
    "all_suggestions": [...],  # 仅在 match_type=search 时提供
    "matched_key": "qwen3"     # 仅在 match_type=fuzzy 时提供
}
```

## 配置管理

所有网站配置集中在 `component/chat/config/web_platform_config.py`：

```python
class WebPlatformConfig:
    # 技术平台
    TECH_PLATFORMS = {
        "qwen": "https://github.com/QwenLM/Qwen",
        ...
    }
    
    # 产品平台
    PRODUCT_PLATFORMS = {
        "产品经理": "https://www.woshipm.com",
        ...
    }
    
    # AI资讯平台
    AI_NEWS_PLATFORMS = {
        "机器之心": "https://www.jiqizhixin.com",
        ...
    }
```

### 添加新网站

只需在配置文件中添加键值对：

```python
# 添加新技术平台
TECH_PLATFORMS = {
    ...
    "new-model": "https://github.com/org/new-model",
}

# 添加新产品平台
PRODUCT_PLATFORMS = {
    ...
    "新产品社区": "https://example.com",
}

# 添加新AI资讯平台
AI_NEWS_PLATFORMS = {
    ...
    "新AI媒体": "https://ai-news.com",
}
```

## 向后兼容

旧的 `suggest_tech_url` API仍然可用（但会输出废弃警告）：

```python
# 旧API（已废弃）
result = web_tools.suggest_tech_url("qwen3")

# 新API（推荐）
result = web_tools.suggest_url("qwen3", mode="technical")
```

## Agent集成

在 `unified_agent.py` 中，工具定义已更新：

```python
WEB_TOOL_DEFINITIONS = [
    {
        "name": "suggest_url",
        "parameters": {
            "keyword": {"type": "string"},
            "mode": {
                "type": "string", 
                "enum": ["technical", "product", "ai_news", "comprehensive"],
                "default": "technical"
            }
        }
    },
    ...
]
```

AI会根据用户问题**自动推断**合适的模式。

## 测试

运行测试脚本验证功能：

```bash
# 测试配置文件
python component/chat/config/web_platform_config.py

# 测试多模式查询
python test/test_web_tools_multimode.py
```

## 统计数据

| 类型 | 平台数量 | 搜索引擎 | 总URL |
|------|---------|---------|-------|
| 技术 | 35 | 4 | 39 |
| 产品 | 22 | 4 | 26 |
| AI资讯 | 25 | 4 | 29 |
| **综合** | **82** | **12** | **94** |

## 未来扩展

- [ ] 添加更多垂直领域平台（金融、医疗、教育等）
- [ ] 支持用户自定义平台映射
- [ ] 添加网站质量评分和优先级
- [ ] 缓存机制优化重复查询
- [ ] 支持多语言平台（英文、中文分离）
- [ ] 集成实时网站可用性检测

## 常见问题

### Q1: 如何让AI自动选择合适的模式？

A: AI会根据问题内容自动判断。你也可以在提示词中明确指定场景，例如：
- "查找**技术文档**..."
- "了解**产品方法论**..."
- "关注**AI行业资讯**..."

### Q2: 综合模式和单一模式有什么区别？

A: 
- **单一模式**：只在特定类型网站中搜索，结果更精准
- **综合模式**：搜索所有类型网站，覆盖更全面，适合初步调研

### Q3: 如果关键词匹配到多个平台怎么办？

A: 系统会返回**第一个匹配**的平台。如果需要多个结果，可以使用"搜索建议"模式。

### Q4: 能否直接访问推荐的URL？

A: 可以，配合 `fetch_url` 工具：

```python
# 1. 获取推荐URL
suggest_result = web_tools.suggest_url("qwen3", mode="technical")
url = suggest_result['suggested_url']

# 2. 访问URL
fetch_result = web_tools.fetch_url(url)
content = fetch_result['content']
```

---

**版本**: v2.0  
**更新日期**: 2025-11-20  
**作者**: AI Video Demo Team
