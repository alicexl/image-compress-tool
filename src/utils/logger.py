"""
日志配置工具
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[Path] = None,
    verbose: bool = True
) -> logging.Logger:
    """
    配置日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        verbose: 是否输出到控制台

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()

    # 控制台处理器
    if verbose:
        # Windows编码修复
        if sys.platform == 'win32':
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logger.level)

        # 使用安全的编码处理
        class SafeStreamHandler(logging.StreamHandler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    # 确保消息是安全的字符串
                    if isinstance(msg, str):
                        msg = msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                    self.stream.write(msg + self.terminator)
                    self.flush()
                except Exception:
                    self.handleError(record)

        # 在Windows上使用安全处理器
        if sys.platform == 'win32':
            console_handler = SafeStreamHandler(sys.stdout)

        if COLORLOG_AVAILABLE:
            # 彩色日志格式
            console_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            # 普通日志格式
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别

            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        except Exception as e:
            logger.error(f"创建日志文件失败 {log_file}: {e}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器
    """
    return logging.getLogger(name)
