"""
批量处理服务
负责批量压缩图片，支持并发处理和智能跳过
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import logging

from ..core.compressor import Compressor
from ..infrastructure.file_manager import FileManager

logger = logging.getLogger(__name__)


class BatchProcessor:
    """批量处理器"""

    def __init__(
        self,
        compressor: Compressor,
        file_manager: FileManager,
        max_workers: Optional[int] = None
    ):
        """
        初始化批量处理器

        Args:
            compressor: 压缩器实例
            file_manager: 文件管理器实例
            max_workers: 最大工作进程数
        """
        self.compressor = compressor
        self.file_manager = file_manager

        import multiprocessing
        if max_workers is None:
            max_workers = multiprocessing.cpu_count()

        self.max_workers = max_workers
        logger.info(f"初始化批量处理器，工作进程数: {max_workers}")

    def scan_files(
        self,
        directory: Path,
        pattern: str = "*.jpg",
        min_size_mb: float = 1.0,
        skip_existing: bool = True,
        output_dir: Optional[Path] = None
    ) -> tuple:
        """
        扫描需要处理的文件

        Args:
            directory: 目录路径
            pattern: 文件名模式
            min_size_mb: 最小文件大小（MB），小于此值的文件直接复制
            skip_existing: 是否跳过已存在的文件
            output_dir: 输出目录

        Returns:
            (大文件列表, 小文件列表, 扫描统计信息)
        """
        large_files = []  # 需要压缩的大文件
        small_files = []  # 需要直接复制的小文件
        skipped_files = []  # 已存在跳过的文件
        invalid_files = []  # 无效的已存在文件

        # 确保使用绝对路径
        directory = directory.resolve()
        if output_dir:
            output_dir = output_dir.resolve()

        try:
            for file_path in directory.glob(pattern):
                # 转换为绝对路径
                file_path = file_path.resolve()

                # 检查输出文件是否已存在
                if skip_existing and output_dir:
                    output_path = output_dir / file_path.name
                    if output_path.exists():
                        # 验证已存在的文件是否是有效的图片
                        if self._is_valid_image(output_path):
                            skipped_files.append(file_path)
                            logger.debug(f"跳过已存在文件: {file_path.name}")
                        else:
                            # 无效文件，需要重新处理
                            invalid_files.append(file_path)
                            logger.warning(f"已存在文件无效，将重新处理: {file_path.name}")
                            # 根据大小分类
                            size_mb = self.file_manager.get_file_size_mb(file_path)
                            if size_mb < min_size_mb:
                                small_files.append(file_path)
                            else:
                                large_files.append(file_path)
                        continue

                # 检查文件大小
                size_mb = self.file_manager.get_file_size_mb(file_path)
                if size_mb < min_size_mb:
                    small_files.append(file_path)
                    logger.debug(f"小文件(直接复制): {file_path.name} ({size_mb:.2f}MB)")
                else:
                    large_files.append(file_path)

            # 统计信息
            stats = {
                'total': len(large_files) + len(small_files) + len(skipped_files),
                'large': len(large_files),
                'small': len(small_files),
                'skipped': len(skipped_files),
                'invalid': len(invalid_files)
            }

            logger.info(
                f"扫描完成: 总计 {stats['total']} 个文件, "
                f"待处理 {len(large_files) + len(small_files)} 个 "
                f"(大文件 {len(large_files)}, 小文件 {len(small_files)}), "
                f"已存在跳过 {len(skipped_files)} 个"
            )

        except Exception as e:
            logger.error(f"扫描文件失败 {directory}: {e}")
            stats = {'total': 0, 'large': 0, 'small': 0, 'skipped': 0, 'invalid': 0}

        return large_files, small_files, stats

    def _is_valid_image(self, file_path: Path) -> bool:
        """
        检查文件是否是有效的图片

        Args:
            file_path: 文件路径

        Returns:
            是否是有效的图片
        """
        try:
            # 检查文件大小
            size = file_path.stat().st_size
            if size <= 0:
                return False

            # 检查文件头，判断是否是有效的 JPEG
            with open(file_path, 'rb') as f:
                header = f.read(2)
                # JPEG 文件以 FF D8 开头
                if header != b'\xff\xd8':
                    return False

                # 检查文件尾，JPEG 文件以 FF D9 结尾
                f.seek(-2, 2)  # 从文件末尾开始
                footer = f.read(2)
                if footer != b'\xff\xd9':
                    return False

            return True

        except Exception as e:
            logger.debug(f"验证图片失败 {file_path}: {e}")
            return False

    def copy_file(
        self,
        input_path: Path,
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        直接复制文件（用于小文件）

        Args:
            input_path: 输入文件路径
            output_dir: 输出目录

        Returns:
            处理结果字典
        """
        # 确保使用绝对路径
        input_path = input_path.resolve()
        output_dir = output_dir.resolve()

        result = {
            'input_path': input_path,
            'status': 'failed',
            'message': '',
            'original_size': 0,
            'compressed_size': 0,
            'compression_ratio': 1.0,
            'quality': 0
        }

        try:
            # 创建输出目录
            if not self.file_manager.ensure_directory(output_dir):
                result['message'] = "创建输出目录失败"
                return result

            # 输出文件路径
            output_path = output_dir / input_path.name

            # 获取原始大小
            result['original_size'] = input_path.stat().st_size

            # 直接复制
            import shutil
            shutil.copy2(input_path, output_path)

            # 获取复制后大小
            result['compressed_size'] = output_path.stat().st_size
            result['message'] = "小文件直接复制"
            result['status'] = 'copied'
            logger.debug(f"复制小文件: {input_path.name}")

        except Exception as e:
            logger.error(f"复制文件异常 {input_path}: {e}")
            result['status'] = 'failed'
            result['message'] = f"异常: {str(e)}"

        return result

    def process_file(
        self,
        input_path: Path,
        output_dir: Path,
        verify: bool = True
    ) -> Dict[str, Any]:
        """
        处理单个文件

        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            verify: 是否验证输出

        Returns:
            处理结果字典
        """
        # 确保使用绝对路径
        input_path = input_path.resolve()
        output_dir = output_dir.resolve()

        result = {
            'input_path': input_path,
            'status': 'failed',
            'message': '',
            'original_size': 0,
            'compressed_size': 0,
            'compression_ratio': 0.0,
            'quality': 0
        }

        try:
            # 创建输出目录
            if not self.file_manager.ensure_directory(output_dir):
                result['message'] = "创建输出目录失败"
                return result

            # 输出文件路径
            output_path = output_dir / input_path.name

            # 验证输入文件
            valid, msg = self.compressor.validate_image(input_path)
            if not valid:
                result['status'] = 'failed'
                result['message'] = msg
                return result

            # 获取原始大小
            result['original_size'] = input_path.stat().st_size

            # 压缩文件
            success, ratio, message = self.compressor.compress(
                input_path,
                output_path
            )

            if not success:
                result['status'] = 'failed'
                result['message'] = message
                return result

            # 获取压缩后大小
            result['compressed_size'] = output_path.stat().st_size
            result['compression_ratio'] = ratio
            result['message'] = message
            result['quality'] = self.compressor.quality

            # 验证输出
            if verify:
                if not self.file_manager._verify_file(
                    output_path, result['compressed_size']
                ):
                    result['status'] = 'failed'
                    result['message'] = "输出文件验证失败"
                    # 清理失败的文件
                    try:
                        output_path.unlink()
                    except:
                        pass
                    return result

            result['status'] = 'success'
            logger.debug(f"处理成功: {input_path.name} (压缩比: {ratio:.2%})")

        except Exception as e:
            logger.error(f"处理文件异常 {input_path}: {e}")
            result['status'] = 'failed'
            result['message'] = f"异常: {str(e)}"

        return result

    def process_batch(
        self,
        input_dir: Path,
        output_dir: Path,
        large_files: List[Path],
        small_files: List[Path] = None,
        verify: bool = True,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        批量处理文件

        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            large_files: 大文件列表（需要压缩）
            small_files: 小文件列表（直接复制）
            verify: 是否验证输出
            progress_callback: 进度回调函数，参数为(completed, total, filename, status)

        Returns:
            批量处理结果
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        if small_files is None:
            small_files = []

        total_files = len(large_files) + len(small_files)

        results = {
            'total': total_files,
            'success': 0,
            'failed': 0,
            'copied': 0,
            'skipped': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'details': []
        }

        # 创建输出目录
        if not self.file_manager.ensure_directory(output_dir):
            results['message'] = "创建输出目录失败"
            return results

        # 线程安全的计数器和锁
        completed_counter = [0]
        counter_lock = threading.Lock()
        results_lock = threading.Lock()
        callback_stopped = [False]  # 控制进度回调

        def process_single_file(file_path: Path, is_large: bool):
            """处理单个文件的包装函数"""
            with counter_lock:
                current_completed = completed_counter[0]
                completed_counter[0] += 1

            # 进度回调
            if progress_callback and not callback_stopped[0]:
                progress_callback(current_completed, total_files, file_path.name, status='processing')

            # 处理文件
            if is_large:
                result = self.process_file(file_path, output_dir, verify=verify)
            else:
                result = self.copy_file(file_path, output_dir)

            # 更新进度
            with counter_lock:
                current_completed = completed_counter[0]

            if progress_callback and not callback_stopped[0]:
                progress_callback(current_completed, total_files, file_path.name, status='completed')

            return result

        # 合并所有文件，标记是否为大文件
        all_files = [(f, True) for f in large_files] + [(f, False) for f in small_files]

        # 使用线程池并发处理
        executor = ThreadPoolExecutor(max_workers=self.max_workers)
        interrupted = False
        try:
            futures = {
                executor.submit(process_single_file, f, is_large): (f, is_large)
                for f, is_large in all_files
            }

            for future in as_completed(futures):
                file_path, is_large = futures[future]
                try:
                    result = future.result()

                    with results_lock:
                        results['details'].append(result)

                        if result['status'] == 'success':
                            results['success'] += 1
                            results['total_original_size'] += result['original_size']
                            results['total_compressed_size'] += result['compressed_size']
                        elif result['status'] == 'copied':
                            results['copied'] += 1
                            results['total_original_size'] += result['original_size']
                            results['total_compressed_size'] += result['compressed_size']
                        else:
                            results['failed'] += 1

                except Exception as e:
                    logger.error(f"处理文件异常: {e}")
                    with results_lock:
                        results['failed'] += 1

        except KeyboardInterrupt:
            interrupted = True
            callback_stopped[0] = True  # 立即停止进度回调
            logger.info("收到中断信号，正在取消未完成的任务...")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        if interrupted:
            results['interrupted'] = True

        logger.info(
            f"批量处理完成: 成功={results['success']}, "
            f"复制={results['copied']}, "
            f"失败={results['failed']}, "
            f"跳过={results['skipped']}"
        )

        return results

    def get_summary(self, results: Dict[str, Any]) -> str:
        """
        生成处理摘要

        Args:
            results: 处理结果

        Returns:
            摘要字符串
        """
        total = results['total']
        success = results['success']
        failed = results['failed']
        skipped = results['skipped']

        total_original_mb = results['total_original_size'] / (1024 * 1024)
        total_compressed_mb = results['total_compressed_size'] / (1024 * 1024)

        if total_original_mb > 0:
            avg_ratio = total_compressed_mb / total_original_mb
            saved_mb = total_original_mb - total_compressed_mb
        else:
            avg_ratio = 0.0
            saved_mb = 0.0

        summary = f"""
=== 处理摘要 ===
总文件数: {total}
成功: {success}
失败: {failed}
跳过: {skipped}

原始总大小: {total_original_mb:.2f} MB
压缩后总大小: {total_compressed_mb:.2f} MB
节省空间: {saved_mb:.2f} MB
平均压缩比: {avg_ratio:.2%}
"""
        return summary
