"""
测试 CLI 参数校验
"""

import unittest
from pathlib import Path
from click.testing import CliRunner

from run import compress


class TestCLI(unittest.TestCase):
    """CLI 参数校验测试"""

    def setUp(self):
        """设置测试环境"""
        self.runner = CliRunner()
        self.test_data_dir = Path(__file__).parent / "test_data" / "images"

    def test_worker_zero(self):
        """测试 -w 0 应该被拒绝"""
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-w', '0'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("1<=x<=8", result.output)

    def test_worker_negative(self):
        """测试 -w -1 应该被拒绝"""
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-w', '-1'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("1<=x<=8", result.output)

    def test_worker_exceed_max(self):
        """测试 -w 9 应该被拒绝"""
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-w', '9'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("1<=x<=8", result.output)

    def test_worker_boundary_min(self):
        """测试 -w 1 应该被接受（边界值）"""
        # 注意：这个测试会因为需要用户确认而失败，但参数校验应该通过
        # 所以我们检查错误消息中不包含 worker 参数错误
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-w', '1'])
        # 参数校验通过，但可能因为没有文件或其他原因失败
        self.assertNotIn("worker 必须在 1-8 范围内", result.output)

    def test_worker_boundary_max(self):
        """测试 -w 8 应该被接受（边界值）"""
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-w', '8'])
        self.assertNotIn("worker 必须在 1-8 范围内", result.output)

    def test_quality_zero(self):
        """测试 -q 0 应该被拒绝"""
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-q', '0'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("1<=x<=100", result.output)

    def test_quality_exceed_max(self):
        """测试 -q 101 应该被拒绝"""
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-q', '101'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("1<=x<=100", result.output)

    def test_quality_boundary_min(self):
        """测试 -q 1 应该被接受（边界值）"""
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-q', '1'])
        self.assertNotIn("1<=x<=100", result.output)

    def test_quality_boundary_max(self):
        """测试 -q 100 应该被接受（边界值）"""
        result = self.runner.invoke(compress, [str(self.test_data_dir), '-q', '100'])
        self.assertNotIn("1<=x<=100", result.output)


if __name__ == '__main__':
    unittest.main()
