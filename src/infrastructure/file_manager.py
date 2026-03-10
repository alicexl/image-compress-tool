"""
文件管理器
处理文件操作和验证
"""

from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """文件管理器"""

    def __init__(self, atomic: bool = True, backup: bool = False):
        """
        初始化文件管理器

        Args:
            atomic: 是否使用原子操作（保留参数兼容性）
            backup: 是否备份原文件（保留参数兼容性）
        """
        logger.info(f"初始化文件管理器")

    def ensure_directory(self, directory: Path) -> bool:
        """
        确保目录存在

        Args:
            directory: 目录路径

        Returns:
            是否成功
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"创建目录失败 {directory}: {e}")
            return False

    def _verify_file(self, file_path: Path, expected_size: int) -> bool:
        """
        验证文件

        Args:
            file_path: 文件路径
            expected_size: 期望的文件大小

        Returns:
            是否有效
        """
        try:
            if not file_path.exists():
                return False

            actual_size = file_path.stat().st_size

            if actual_size <= 0:
                logger.error(f"文件大小为0: {file_path}")
                return False

            if abs(actual_size - expected_size) > expected_size * 0.1:
                logger.warning(
                    f"文件大小不匹配: {file_path}, "
                    f"期望={expected_size}, 实际={actual_size}"
                )

            return True

        except Exception as e:
            logger.error(f"文件验证失败 {file_path}: {e}")
            return False

    def cleanup_temp_files(self, directory: Path, pattern: str = "*.tmp") -> int:
        """
        清理临时文件

        Args:
            directory: 目录路径
            pattern: 文件模式

        Returns:
            清理的文件数量
        """
        count = 0
        try:
            for temp_file in directory.glob(pattern):
                try:
                    temp_file.unlink()
                    count += 1
                except Exception as e:
                    logger.warning(f"删除临时文件失败 {temp_file}: {e}")

            if count > 0:
                logger.info(f"清理了 {count} 个临时文件")

        except Exception as e:
            logger.error(f"清理临时文件失败 {directory}: {e}")

        return count

    def get_file_size_mb(self, file_path: Path) -> float:
        """
        获取文件大小（MB）

        Args:
            file_path: 文件路径

        Returns:
            文件大小（MB）
        """
        try:
            size_bytes = file_path.stat().st_size
            return size_bytes / (1024 * 1024)
        except Exception as e:
            logger.error(f"获取文件大小失败 {file_path}: {e}")
            return 0.0
