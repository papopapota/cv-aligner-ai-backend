from abc import ABC, abstractmethod


class FileStoragePort(ABC):
    @abstractmethod
    async def ensure_bucket(self) -> None:
        """Create the configured bucket when it does not exist yet."""

    @abstractmethod
    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        """Store an object under ``key``."""

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Return the bytes stored under ``key``."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete the object stored under ``key``. Missing keys are ignored."""

    @abstractmethod
    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Return a temporary URL to download the object under ``key``."""
