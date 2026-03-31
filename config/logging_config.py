"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 日志配置需求
Output: 日志配置对象
Pos: 日志系统配置管理
"""

import logging
import sys


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[37m', 'INFO': '\033[37m',
        'WARNING': '\033[33m', 'ERROR': '\033[31m', 'RESET': '\033[0m'
    }

    def format(self, record):
        message = super().format(record)
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        return f"{color}{message}{self.COLORS['RESET']}"


def setup_logging():
    """全局日志配置，项目启动时调用一次"""
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    # root_logger.setLevel(logging.INFO)
    root_logger.setLevel(logging.DEBUG)


def get_logger(name):
    """获取logger实例"""
    return logging.getLogger(name)
