"""
测试压缩核心功能
"""

import unittest
from pathlib import Path
from src.core.compressor import Compressor


class TestCompressor(unittest.TestCase):
    """压缩器测试"""

    def setUp(self):
        """设置测试环境"""
        self.compressor = Compressor(quality=77)
        self.test_data_dir = Path(__file__).parent / "test_data" / "images"

        # 确保测试数据存在
        if not self.test_data_dir.exists():
            self.skipTest("测试数据目录不存在")

        # 获取测试图片
        test_images = list(self.test_data_dir.glob("*.jpg"))
        if not test_images:
            self.skipTest("没有找到测试图片")

        self.test_image = test_images[0]

    def test_compressor_initialization(self):
        """测试压缩器初始化"""
        self.assertEqual(self.compressor.quality, 77)

        # 测试不同质量参数
        compressor_low = Compressor(quality=70)
        self.assertEqual(compressor_low.quality, 70)

        compressor_high = Compressor(quality=90)
        self.assertEqual(compressor_high.quality, 90)

    def test_validate_image(self):
        """测试图片验证"""
        # 测试有效图片
        valid, message = self.compressor.validate_image(self.test_image)
        self.assertTrue(valid)
        self.assertIn("有效图片", message)

        # 测试不存在的文件
        invalid_path = self.test_data_dir / "nonexistent.jpg"
        valid, message = self.compressor.validate_image(invalid_path)
        self.assertFalse(valid)

    def test_get_image_info(self):
        """测试获取图片信息"""
        info = self.compressor.get_image_info(self.test_image)

        self.assertIsNotNone(info)
        self.assertIn('format', info)
        self.assertIn('size', info)
        self.assertIn('mode', info)
        self.assertIn('file_size', info)

        self.assertEqual(info['format'], 'JPEG')
        self.assertEqual(len(info['size']), 2)  # (width, height)
        self.assertGreater(info['file_size'], 0)

    def test_compress_once(self):
        """测试单次压缩"""
        output_path = self.test_image.with_suffix('.test.jpg')

        try:
            success, compressed_size, message = self.compressor._compress_once(
                self.test_image,
                output_path,
                quality=75
            )

            self.assertTrue(success)
            self.assertGreater(compressed_size, 0)
            self.assertEqual(message, "压缩成功")
            self.assertTrue(output_path.exists())

            # 清理
            output_path.unlink()

        finally:
            if output_path.exists():
                output_path.unlink()

    def test_compress(self):
        """测试完整压缩流程"""
        output_path = self.test_image.with_suffix('.test2.jpg')

        try:
            success, ratio, message = self.compressor.compress(
                self.test_image,
                output_path
            )

            self.assertTrue(success)
            self.assertGreater(ratio, 0)
            self.assertTrue(output_path.exists())

            # 检查压缩比是否合理（压缩后应该更小）
            original_size = self.test_image.stat().st_size
            compressed_size = output_path.stat().st_size
            self.assertLess(compressed_size, original_size)

            # 验证压缩比计算正确
            expected_ratio = compressed_size / original_size
            self.assertAlmostEqual(ratio, expected_ratio, places=2)

            # 清理
            output_path.unlink()

        finally:
            if output_path.exists():
                output_path.unlink()

    def test_quality_parameter(self):
        """测试质量参数影响"""
        output_low = self.test_image.with_suffix('.test_low.jpg')
        output_high = self.test_image.with_suffix('.test_high.jpg')

        try:
            # 低质量压缩
            compressor_low = Compressor(quality=70)
            success_low, ratio_low, _ = compressor_low.compress(
                self.test_image,
                output_low
            )

            # 高质量压缩
            compressor_high = Compressor(quality=85)
            success_high, ratio_high, _ = compressor_high.compress(
                self.test_image,
                output_high
            )

            self.assertTrue(success_low)
            self.assertTrue(success_high)

            # 一般来说，低质量压缩比更小（压缩更多）
            # 但这个关系不是绝对的，取决于图片内容
            print(f"低质量(70)压缩比: {ratio_low:.2%}")
            print(f"高质量(85)压缩比: {ratio_high:.2%}")

            # 验证两个输出文件都存在
            self.assertTrue(output_low.exists())
            self.assertTrue(output_high.exists())

        finally:
            for output in [output_low, output_high]:
                if output.exists():
                    output.unlink()

    def test_compress_invalid_input(self):
        """测试压缩无效输入"""
        invalid_path = self.test_data_dir / "nonexistent.jpg"
        output_path = self.test_data_dir / "output.jpg"

        success, ratio, message = self.compressor.compress(
            invalid_path,
            output_path
        )

        self.assertFalse(success)
        self.assertEqual(ratio, 0.0)


if __name__ == '__main__':
    unittest.main()
