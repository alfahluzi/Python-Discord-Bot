from abc import ABC, abstractmethod
from typing import Any

class BaseTool(ABC):
    """Kelas dasar untuk semua tools LangChain"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nama tool"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Deskripsi tool"""
        pass
    
    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Metode untuk menjalankan tool"""
        pass 