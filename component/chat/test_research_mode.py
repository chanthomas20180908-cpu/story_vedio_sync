#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 测试数据或模块
Output: 测试结果
Pos: 测试文件：test_research_mode.py
"""

"""
测试网络调研模式识别
验证agent能否正确识别PRODUCT_PLATFORMS和AI_NEWS关键词
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent  # 回到pythonProject目录
sys.path.insert(0, str(project_root))

from component.chat.core.unified_agent import UnifiedAgent
from component.chat.config.agent_config import AgentMode
from config.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def test_research_modes():
    """测试不同调研模式"""
    
    # 从环境变量获取API密钥
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY 未配置")
    
    # 初始化agent - 使用默认产品专家模式
    agent = UnifiedAgent(
        api_key=api_key,
        model_type="qwen",
        model="qwen-plus",
        mode=AgentMode.FULL,  # 启用知识库和网络工具
        system_prompt_type="product_expert"
    )
    
    # 测试用例 - 只测试关键词识别
    test_cases = [
        {
            "name": "产品平台调研 (PRODUCT_PLATFORMS关键词)",
            "query": "请快速查找一个AI相册产品案例，使用PRODUCT_PLATFORMS，只需要一个代表性案例即可",
            "expected_mode": "product"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"测试 {i}: {test_case['name']}")
        logger.info(f"查询: {test_case['query']}")
        logger.info(f"{'='*70}\n")
        
        try:
            # 执行单轮对话
            result = agent.chat(
                user_input=test_case['query'],
                conversation_history=[],
                max_iterations=3  # 减少迭代次数，只看是否能正确调用suggest_url
            )
            
            logger.info(f"\n结果:")
            logger.info(f"- 模型响应: {result.get('answer', '')[:500]}...")
            logger.info(f"- 工具调用次数: {len(result.get('tool_calls', []))}")
            logger.info(f"- 迭代次数: {result.get('iterations', 0)}")
            
            # 分析工具调用
            tool_calls = result.get('tool_calls', [])
            suggest_url_calls = [
                call for call in tool_calls 
                if call.get('name') == 'suggest_url'  # 注意：字段名是'name'不是'function_name'
            ]
            
            if suggest_url_calls:
                logger.info(f"\n✅ suggest_url 调用 {len(suggest_url_calls)} 次:")
                for call in suggest_url_calls:
                    args = call.get('arguments', {})
                    logger.info(f"  - keyword: {args.get('keyword')}, mode: {args.get('mode')}")
            else:
                logger.warning("❌ 没有调用 suggest_url 工具")
            
            # 统计所有工具调用
            tool_summary = {}
            for call in tool_calls:
                tool_name = call.get('name', 'unknown')
                tool_summary[tool_name] = tool_summary.get(tool_name, 0) + 1
            
            if tool_summary:
                logger.info(f"\n工具调用统计:")
                for tool_name, count in tool_summary.items():
                    logger.info(f"  - {tool_name}: {count} 次")
            
        except Exception as e:
            logger.error(f"测试失败: {e}", exc_info=True)
        
        logger.info("\n")


if __name__ == "__main__":
    logger.info("开始测试网络调研模式识别...")
    test_research_modes()
    logger.info("测试完成!")
