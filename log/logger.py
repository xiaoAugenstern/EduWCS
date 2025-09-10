import logging
import os

def create_logger(log_filename):
    logger = logging.getLogger(log_filename)
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_filename)  # 存储日志文件的路径
    handler = logging.FileHandler(log_path)
    handler.setLevel(logging.DEBUG)  # 设置日志级别为 DEBUG
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

# 创建日志记录器实例
guohan_correct_logger = create_logger('guohan_correct.log')
guohan_correct_error_logger = create_logger('guohan_correct_error.log')