# 网络访问功能说明

## 概述

为AI助手添加了**网络访问能力**，现在可以：
- 🌐 访问任意网页并提取内容
- 📄 获取网页摘要
- 🔍 在网页中搜索关键词
- 🤖 结合知识库进行综合分析

## 核心组件

### 1. WebTools (`web_tools.py`)
网络访问工具类，提供三大核心功能：

#### 方法
- **`fetch_url(url, extract_main=True)`**: 访问URL并获取内容
  - 自动识别编码
  - 智能提取主要内容（去除导航、广告等）
  - 支持最大内容长度限制（默认50000字符）
  - 返回：标题、描述、内容、长度等

- **`get_page_summary(url, max_paragraphs=5)`**: 获取网页摘要
  - 提取前N段内容
  - 过滤短段落（< 50字符）
  - 返回：标题、描述、摘要、段落数

- **`search_in_page(url, keyword, context_chars=200)`**: 在网页中搜索关键词
  - 查找所有匹配位置
  - 提取上下文内容
  - 限制最多10个结果
  - 返回：匹配次数、上下文列表

### 2. EnhancedAgent (`enhanced_agent.py`)
增强版Agent，整合：
- ✅ 知识库工具（文档CRUD）
- ✅ 网络访问工具（网页抓取）
- ✅ 多轮工具调用（最多10轮）
- ✅ 智能任务分解

#### 工具定义
```python
# 知识库工具
- list_documents: 列出文档
- read_document: 读取文档
- create_document: 创建文档
- search_in_documents: 搜索文档

# 网络访问工具
- fetch_url: 访问网页
- get_page_summary: 获取摘要
- search_in_page: 搜索网页内容
```

### 3. 交互式界面 (`chat_with_web.py`)
带网络访问功能的聊天界面：
- 🔧 自动工具选择
- 📊 执行过程可视化
- 🌐 网络/知识库工具区分
- ⚙️ 支持配置化显示

## 使用方法

### 方法1: 交互式对话
```bash
python component/chat/chat_with_web.py
```

### 方法2: 编程调用
```python
from component.chat.knowledge_base.enhanced_agent import EnhancedAgent

api_key = "your_api_key"
agent = EnhancedAgent(api_key=api_key, model="qwen-plus")

# 访问网页
result = agent.chat("访问 https://example.com 并分析内容")
print(result['answer'])

# 知识库+网络
result = agent.chat("搜索知识库中的竞品信息，并访问他们的官网进行对比")
print(result['answer'])
```

## 使用示例

### 示例1: 访问网页
```
👤 您: 访问 https://www.baidu.com 并告诉我这是什么网站

🤖 助手: 百度（https://www.baidu.com）是中国最大的搜索引擎网站，
提供网页搜索、图片搜索、新闻搜索等多种搜索服务...

🔧 执行了 1 个工具调用（共 2 轮）:
   1. 🌐 fetch_url - ✅
      URL: https://www.baidu.com
      内容长度: 1234 字符
```

### 示例2: 获取网页摘要
```
👤 您: 给我看看 https://example.com/article 的摘要

🤖 助手: 该文章主要介绍了...（前5段内容）

🔧 执行了 1 个工具调用（共 2 轮）:
   1. 🌐 get_page_summary - ✅
```

### 示例3: 搜索网页内容
```
👤 您: 在 https://example.com 中搜索关键词 "AI"

🤖 助手: 在该网页中找到3处关于"AI"的内容：
1. ...AI技术的发展...
2. ...人工智能应用...
3. ...AI模型训练...

🔧 执行了 1 个工具调用（共 2 轮）:
   1. 🌐 search_in_page - ✅
```

### 示例4: 综合分析（知识库+网络）
```
👤 您: 读取知识库中的竞品分析，然后访问百度慧播星的官网，对比我们的优势

🤖 助手: [综合分析结果...]

🔧 执行了 3 个工具调用（共 4 轮）:
   1. 📁 read_document - ✅
   2. 🌐 fetch_url - ✅
   3. 📁 create_document - ✅
```

## 配置参数

### WebTools 配置
```python
WebTools(
    timeout=30,              # 请求超时（秒）
    max_content_length=50000 # 最大内容长度（字符）
)
```

### EnhancedAgent 配置
```python
EnhancedAgent(
    api_key="your_key",
    model_type="qwen",       # qwen/deepseek
    model="qwen-plus",       # 模型名称
    kb_root=None            # 知识库路径（可选）
)
```

### 聊天配置
```python
agent.chat(
    user_input="...",
    conversation_history=[],  # 对话历史
    max_iterations=10         # 最大工具调用轮数
)
```

## 安全注意事项

1. **URL验证**: 自动验证URL格式
2. **超时控制**: 默认30秒超时，防止长时间挂起
3. **内容长度限制**: 默认最大50000字符，防止内存溢出
4. **错误处理**: 完善的异常捕获和错误提示
5. **User-Agent**: 使用标准浏览器UA，避免被反爬

## 技术栈

- **网络请求**: requests
- **HTML解析**: BeautifulSoup4
- **AI模型**: Qwen/DeepSeek（通过DashScope API）
- **工具调用**: OpenAI Function Calling协议

## 依赖安装

```bash
pip install beautifulsoup4 requests
```

## 常见问题

### Q: 为什么有些网页无法访问？
A: 可能原因：
- 网站需要登录
- 有反爬虫机制
- 网络超时或连接失败
- 网站需要JavaScript渲染

### Q: 如何处理需要JavaScript的网页？
A: 当前版本不支持JavaScript渲染，建议：
- 使用API接口（如果网站提供）
- 使用Selenium/Playwright（需额外开发）
- 寻找静态版本或镜像站点

### Q: 内容过长被截断怎么办？
A: 可以：
- 增加`max_content_length`参数
- 使用`get_page_summary`获取摘要
- 分段读取（多次调用）

### Q: 如何提高网页抓取成功率？
A: 建议：
- 增加超时时间
- 添加重试机制
- 使用代理IP
- 调整User-Agent

## 扩展建议

### 未来可添加功能
1. **JavaScript渲染**: 集成Selenium/Playwright
2. **代理支持**: 支持HTTP/SOCKS代理
3. **重试机制**: 自动重试失败请求
4. **缓存机制**: 缓存网页内容减少重复请求
5. **PDF支持**: 支持抓取和解析PDF文件
6. **图片分析**: 提取和分析网页图片
7. **表格提取**: 智能提取网页表格数据
8. **链接爬取**: 递归抓取相关链接

### 性能优化
1. 使用异步请求（aiohttp）
2. 并发抓取多个URL
3. 智能内容压缩
4. 增量更新机制

## 更新日志

### v1.0.0 (2025-10-28)
- ✅ 初始版本
- ✅ 基础网页抓取功能
- ✅ 内容提取和清理
- ✅ 网页摘要生成
- ✅ 关键词搜索
- ✅ 集成到EnhancedAgent
- ✅ 交互式界面

---

**作者**: AI Video Demo Team  
**最后更新**: 2025-10-28  
**反馈**: 如有问题或建议，欢迎提Issue
