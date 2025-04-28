import logging
import os
from logging.handlers import RotatingFileHandler

class Logger:
    """Kelas untuk mengelola logging di aplikasi"""
    def __init__(self, name:str):
        super().__init__()
        # Jika name adalah path file, gunakan path relatif dari src
        if "src\\" in name:
            name = name.split("src\\")[1]
        name = name.replace('.py', '')
        if "\\" in name:
            name = name.replace("\\", '.')

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Buat direktori logs jika belum ada
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        # Format log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler untuk menyimpan log ke file
        log_file = f"logs/{name.replace('.', '_')}.log"
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Console handler untuk menampilkan log di console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Tambahkan handlers ke logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message):
        """Log level debug"""
        self.logger.debug(message)
    
    def info(self, message):
        """Log level info"""
        self.logger.info(message)
    
    def warning(self, message):
        """Log level warning"""
        self.logger.warning(message)
    
    def error(self, message):
        """Log level error"""
        self.logger.error(message)
    
    def critical(self, message):
        """Log level critical"""
        self.logger.critical(message)
    
    def exception(self, message):
        """Log exception dengan traceback"""
        self.logger.exception(message) 