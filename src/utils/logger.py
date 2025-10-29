import logging
import os
from datetime import datetime
from config.settings import settings

def setup_logger():
    """设置日志配置"""
    # 创建logs目录
    os.makedirs("logs", exist_ok=True)

    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 清除现有的handlers
    root_logger.handlers.clear()

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件handler
    log_filename = f"logs/{settings.LOG_FILE}"
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 错误日志单独文件
    error_log_filename = f"logs/error_{datetime.now().strftime('%Y%m')}.log"
    error_handler = logging.FileHandler(error_log_filename, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    return root_logger

def get_logger(name: str = None):
    """获取logger实例"""
    return logging.getLogger(name or __name__)

# 全局异常处理器
def setup_exception_handler():
    """设置全局异常处理器"""
    logger = get_logger('exception_handler')

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            logger.info("程序被用户中断")
            return

        logger.error(
            "未捕获的异常",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    import sys
    sys.excepthook = handle_exception

# 日志装饰器
def log_function_call(func):
    """装饰器：记录函数调用"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"调用函数: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            raise
    return wrapper

# 性能监控装饰器
def log_performance(func):
    """装饰器：记录函数执行时间"""
    import time
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"函数 {func.__name__} 执行时间: {execution_time:.2f} 秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.2f} 秒, 错误: {e}")
            raise
    return wrapper