"""
测试批量处理功能
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from src.core.compressor import Compressor
from src.infrastructure.file_manager import FileManager
from src.services.batch_processor import BatchProcessor


class TestBatchProcessor(unittest.TestCase):
    """批量处理器测试"""

    def setUp(self):
        """设置测试环境"""
        self.test_data_dir = Path(__file__).parent / "test_data" / "images"

        # 确保测试数据存在
        if not self.test_data_dir.exists():
            self.skipTest("测试数据目录不存在")

        # 创建临时输出目录
        self.temp_dir = Path(tempfile.mkdtemp())

        # 初始化组件
        self.compressor = Compressor(quality=77)
        self.file_manager = FileManager(atomic=True, backup=False)
        self.batch_processor = BatchProcessor(
            compressor=self.compressor,
            file_manager=self.file_manager,
            max_workers=1
        )

    def tearDown(self):
        """清理测试环境"""
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"清理临时目录失败: {e}")
                import time
                time.sleep(1)
                try:
                    shutil.rmtree(self.temp_dir)
                except:
                    pass

    def test_scan_files(self):
        """测试文件扫描"""
        large_files, small_files, video_files, stats = self.batch_processor.scan_files(
            self.test_data_dir,
            pattern="*.jpg",
            min_size_mb=0.1,
            skip_existing=False
        )

        total_files = len(large_files) + len(small_files)
        self.assertGreater(total_files, 0)
        self.assertEqual(stats['total'], total_files)

        for file_path in large_files + small_files:
            self.assertTrue(file_path.suffix.lower() in ['.jpg', '.jpeg'])

    def test_scan_with_filter(self):
        """测试带过滤的文件扫描"""
        large_files, small_files, video_files, stats = self.batch_processor.scan_files(
            self.test_data_dir,
            pattern="*.jpg",
            min_size_mb=100.0,
            skip_existing=False
        )

        self.assertEqual(len(large_files), 0)

    def test_process_single_file(self):
        """测试处理单个文件"""
        large_files, small_files, video_files, stats = self.batch_processor.scan_files(
            self.test_data_dir,
            pattern="*.jpg",
            min_size_mb=0.1,
            skip_existing=False
        )

        files = large_files if large_files else small_files
        if not files:
            self.skipTest("没有找到测试图片")

        test_file = files[0]
        output_dir = self.temp_dir / "output"

        result = self.batch_processor.process_file(
            test_file,
            output_dir,
            verify=True
        )

        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['compressed_size'], 0)
        self.assertGreater(result['compression_ratio'], 0)

        output_file = output_dir / test_file.name
        self.assertTrue(output_file.exists())
        self.assertLess(result['compressed_size'], result['original_size'])

    def test_batch_process(self):
        """测试批量处理"""
        large_files, small_files, video_files, stats = self.batch_processor.scan_files(
            self.test_data_dir,
            pattern="*.jpg",
            min_size_mb=0.1,
            skip_existing=False
        )

        files = large_files if large_files else small_files
        if not files:
            self.skipTest("没有找到测试图片")

        output_dir = self.temp_dir / "batch_output"

        progress_calls = []

        def progress_callback(completed, total, filename, status='completed'):
            progress_calls.append({
                'completed': completed,
                'total': total,
                'filename': filename,
                'status': status
            })

        results = self.batch_processor.process_batch(
            input_dir=self.test_data_dir,
            output_dir=output_dir,
            large_files=large_files,
            small_files=small_files,
            verify=True,
            progress_callback=progress_callback
        )

        total_files = len(large_files) + len(small_files)

        self.assertEqual(results['total'], total_files)
        self.assertGreater(results['success'] + results['copied'], 0)
        self.assertEqual(results['failed'], 0)

        for file_path in large_files + small_files:
            output_file = output_dir / file_path.name
            self.assertTrue(output_file.exists())

        self.assertEqual(len(progress_calls), total_files * 2)
        self.assertEqual(progress_calls[0]['status'], 'processing')
        self.assertEqual(progress_calls[0]['completed'], 0)
        self.assertEqual(progress_calls[-1]['status'], 'completed')
        self.assertEqual(progress_calls[-1]['completed'], total_files)

    def test_progress_callback_signature(self):
        """测试进度回调函数签名"""
        large_files, small_files, video_files, stats = self.batch_processor.scan_files(
            self.test_data_dir,
            pattern="*.jpg",
            min_size_mb=0.1,
            skip_existing=False
        )

        files = large_files if large_files else small_files
        if not files:
            self.skipTest("没有找到测试图片")

        output_dir = self.temp_dir / "callback_test"

        callback_args = []

        def capture_callback(completed, total, filename, status='completed'):
            callback_args.append((completed, total, filename, status))

        self.batch_processor.process_batch(
            input_dir=self.test_data_dir,
            output_dir=output_dir,
            large_files=files[:1],
            small_files=[],
            progress_callback=capture_callback
        )

        self.assertEqual(len(callback_args), 2)

        completed, total, filename, status = callback_args[0]
        self.assertEqual(status, 'processing')
        self.assertEqual(total, 1)
        self.assertIsNotNone(filename)

        completed, total, filename, status = callback_args[1]
        self.assertEqual(status, 'completed')
        self.assertEqual(completed, 1)
        self.assertEqual(total, 1)

    def test_skip_existing(self):
        """测试跳过已存在文件"""
        large_files, small_files, video_files, stats = self.batch_processor.scan_files(
            self.test_data_dir,
            pattern="*.jpg",
            min_size_mb=0.1,
            skip_existing=False
        )

        files = large_files if large_files else small_files
        if not files:
            self.skipTest("没有找到测试图片")

        test_file = files[0]
        output_dir = self.temp_dir / "output2"

        result1 = self.batch_processor.process_file(
            test_file,
            output_dir,
            verify=True
        )
        self.assertEqual(result1['status'], 'success')

        large_files2, small_files2, video_files2, stats2 = self.batch_processor.scan_files(
            self.test_data_dir,
            pattern="*.jpg",
            min_size_mb=0.1,
            skip_existing=True,
            output_dir=output_dir
        )

        all_files2 = large_files2 + small_files2
        self.assertNotIn(test_file.resolve(), [f.resolve() for f in all_files2])

    def test_get_summary(self):
        """测试生成摘要"""
        results = {
            'total': 10,
            'success': 8,
            'failed': 1,
            'skipped': 1,
            'total_original_size': 100000000,
            'total_compressed_size': 25000000
        }

        summary = self.batch_processor.get_summary(results)

        self.assertIn("总文件数: 10", summary)
        self.assertIn("成功: 8", summary)
        self.assertIn("失败: 1", summary)
        self.assertIn("跳过: 1", summary)
        self.assertIn("平均压缩比", summary)

    def test_keyboard_interrupt(self):
        """测试 Ctrl+C 中断处理"""
        from unittest.mock import patch

        large_files, small_files, video_files, stats = self.batch_processor.scan_files(
            self.test_data_dir,
            pattern="*.jpg",
            min_size_mb=0.1,
            skip_existing=False
        )

        files = large_files if large_files else small_files
        if not files:
            self.skipTest("没有找到测试图片")

        output_dir = self.temp_dir / "interrupt_test"

        # 模拟在处理第二个文件时触发 KeyboardInterrupt
        call_count = [0]
        original_process_file = self.batch_processor.process_file

        def mock_process_file(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise KeyboardInterrupt()
            return original_process_file(*args, **kwargs)

        with patch.object(self.batch_processor, 'process_file', side_effect=mock_process_file):
            results = self.batch_processor.process_batch(
                input_dir=self.test_data_dir,
                output_dir=output_dir,
                large_files=files,
                small_files=[],
                verify=True
            )

        # 验证至少处理了一个文件
        self.assertGreater(call_count[0], 0)
        # 验证中断标志被设置
        self.assertTrue(results.get('interrupted', False))


if __name__ == '__main__':
    unittest.main()
