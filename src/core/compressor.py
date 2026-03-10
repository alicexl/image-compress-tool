"""
图片压缩核心引擎
提供单张图片的压缩功能
"""

from PIL import Image
from pathlib import Path
from typing import Tuple, Optional
import logging

# 禁用 PIL 像素限制检查
Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger(__name__)


class Compressor:
    """图片压缩器"""

    def __init__(self, quality: int = 77):
        """
        初始化压缩器

        Args:
            quality: JPEG压缩质量 (1-100)
        """
        self.quality = quality
        logger.info(f"初始化压缩器，质量参数: {quality}")

    def compress(
        self,
        input_path: Path,
        output_path: Path
    ) -> Tuple[bool, float, str]:
        """
        压缩单张图片（简化版）

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径

        Returns:
            (是否成功, 压缩比, 消息)
        """
        try:
            # 获取原文件大小
            original_size = input_path.stat().st_size

            # 直接使用设定的质量参数压缩
            success, compressed_size, message = self._compress_once(
                input_path, output_path, self.quality
            )

            if not success:
                return False, 0.0, message

            # 计算压缩比
            ratio = compressed_size / original_size

            logger.debug(
                f"压缩成功: 质量={self.quality}, 压缩比={ratio:.2%}"
            )

            return True, ratio, f"压缩成功 (质量: {self.quality})"

        except Exception as e:
            logger.error(f"压缩失败 {input_path}: {e}")
            return False, 0.0, f"异常: {str(e)}"

    def _compress_once(
        self,
        input_path: Path,
        output_path: Path,
        quality: int
    ) -> Tuple[bool, int, str]:
        """
        执行一次压缩

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            quality: 压缩质量

        Returns:
            (是否成功, 文件大小, 消息)
        """
        try:
            # 打开图片
            with Image.open(input_path) as img:
                # 保存为JPEG
                img.save(
                    output_path,
                    'JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True
                )

            # 验证输出文件
            if not output_path.exists():
                return False, 0, "输出文件未创建"

            compressed_size = output_path.stat().st_size
            return True, compressed_size, "压缩成功"

        except Exception as e:
            logger.error(f"压缩失败 {input_path}: {e}")
            # 清理可能创建的不完整文件
            if output_path.exists():
                try:
                    output_path.unlink()
                except:
                    pass
            return False, 0, f"异常: {str(e)}"

    def validate_image(self, image_path: Path) -> Tuple[bool, str]:
        """
        验证图片是否可以处理

        Args:
            image_path: 图片路径

        Returns:
            (是否有效, 消息)
        """
        try:
            with Image.open(image_path) as img:
                # 验证图片格式
                if img.format != 'JPEG':
                    return False, f"不支持的格式: {img.format}"

                # 验证图片尺寸
                width, height = img.size
                if width == 0 or height == 0:
                    return False, f"无效的尺寸: {width}x{height}"

                return True, f"有效图片 ({width}x{height})"

        except Exception as e:
            return False, f"验证失败: {str(e)}"

    def get_image_info(self, image_path: Path) -> Optional[dict]:
        """
        获取图片信息

        Args:
            image_path: 图片路径

        Returns:
            图片信息字典，失败返回None
        """
        try:
            with Image.open(image_path) as img:
                return {
                    'format': img.format,
                    'size': img.size,
                    'mode': img.mode,
                    'file_size': image_path.stat().st_size
                }
        except Exception as e:
            logger.error(f"获取图片信息失败 {image_path}: {e}")
            return None
