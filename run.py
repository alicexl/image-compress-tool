#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图片压缩工具
"""

import click
import logging
from pathlib import Path
from datetime import datetime

from src.core.compressor import Compressor
from src.services.batch_processor import BatchProcessor
from src.infrastructure.file_manager import FileManager
from src.utils.logger import setup_logger

# 支持的图片文件扩展名
IMAGE_EXTENSIONS = {'.jpg', '.jpeg'}


def _detect_directory_structure(input_dir: Path) -> tuple:
    """
    检测目录结构

    Args:
        input_dir: 输入目录

    Returns:
        (image_files, subdirs) - 一级图片文件列表, 子目录列表
    """
    image_files = []
    subdirs = []

    for item in input_dir.iterdir():
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            image_files.append(item)
        elif item.is_dir():
            # 检查子目录是否包含图片或视频
            has_media = any(
                f.suffix.lower() in IMAGE_EXTENSIONS or
                f.suffix.lower() in {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpeg', '.mpg', '.3gp'}
                for f in item.iterdir() if f.is_file()
            )
            if has_media:
                subdirs.append(item)

    return image_files, subdirs


@click.command()
@click.argument('input_dir', type=click.Path(exists=True, path_type=Path))
@click.option(
    '-q', '--quality',
    default=80,
    type=click.IntRange(1, 100),
    show_default=True,
    help='压缩质量 (1-100)'
)
@click.option(
    '-w', '--worker',
    default=4,
    type=click.IntRange(1, 8),
    show_default=True,
    help='并发数 (1-8)'
)
@click.option(
    '-o', '--output',
    type=click.Path(path_type=Path),
    default=None,
    help='输出目录 (默认: {input_dir}_compressed)'
)
@click.option(
    '-f', '--force',
    is_flag=True,
    default=False,
    help='强制覆盖已存在的文件'
)
def compress(
    input_dir: Path,
    quality: int,
    worker: int,
    output: Path = None,
    force: bool = False
):
    """
    批量压缩图片

    INPUT_DIR: 图片所在目录
    """

    # 固定值
    pattern = '*.jpg'
    atomic = True
    log_level = 'INFO'
    log_file = 'compress.log'

    # 转换为绝对路径
    input_dir = input_dir.resolve()

    # 设置日志
    logger = setup_logger(
        'compress_tool',
        level=log_level,
        log_file=Path(log_file),
        verbose=True
    )

    # 打印启动信息
    logger.info("=" * 50)
    logger.info("图片压缩工具")
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"质量参数: {quality}")
    logger.info(f"并发数: {worker}")
    logger.info(f"覆盖模式: {'是' if force else '否'}")
    logger.info("=" * 50)

    start_time = datetime.now()

    try:
        # 检测目录结构
        logger.info("检测目录结构...")
        root_images, subdirs = _detect_directory_structure(input_dir)

        # 判断处理模式
        has_subdirs = len(subdirs) > 0
        has_root_images = len(root_images) > 0

        if not has_subdirs:
            # 模式1: 纯图片目录 - 原有逻辑
            logger.info("模式: 纯图片目录")
            _process_single_directory(
                input_dir=input_dir,
                output=output,
                quality=quality,
                worker=worker,
                force=force,
                logger=logger,
                pattern=pattern,
                atomic=atomic
            )
        else:
            # 模式2/3: 有子目录
            logger.info(f"模式: 多级目录 (子目录 {len(subdirs)} 个, 一级图片 {len(root_images)} 个)")

            # 显示扫描结果
            print(f"\n扫描结果:")
            print(f"  - 子目录: {len(subdirs)} 个")
            for subdir in subdirs:
                print(f"    • {subdir.name}/")
            if has_root_images:
                print(f"  - 一级图片: {len(root_images)} 个 (将原地压缩)")

            # 用户确认
            print(f"\n即将处理:")
            for subdir in subdirs:
                output_name = f"{subdir.name}_compressed"
                print(f"  - {subdir.name}/ → {output_name}/")
            if has_root_images:
                print(f"  - 一级图片: 原地压缩")

            if not click.confirm("\n确认开始处理", default=True):
                logger.info("用户取消操作")
                return

            # 初始化组件
            compressor = Compressor(quality=quality)
            file_manager = FileManager(atomic=atomic, backup=False)
            batch_processor = BatchProcessor(
                compressor=compressor,
                file_manager=file_manager,
                max_workers=worker
            )

            total_results = {
                'subdirs_success': 0,
                'subdirs_failed': 0,
                'inplace_success': 0,
                'inplace_failed': 0,
                'total_original_size': 0,
                'total_compressed_size': 0,
            }

            # 处理每个子目录
            for subdir in subdirs:
                subdir_output = input_dir / f"{subdir.name}_compressed"
                print(f"\n处理子目录: {subdir.name}/")

                # 扫描子目录
                large_files, small_files, video_files, scan_stats = batch_processor.scan_files(
                    subdir,
                    pattern=pattern,
                    min_size_mb=1.0,
                    skip_existing=not force,
                    output_dir=subdir_output
                )

                total_files = len(large_files) + len(small_files)

                if total_files == 0 and len(video_files) == 0:
                    print(f"  跳过: 没有需要处理的文件")
                    continue

                # 压缩图片
                results = {'success': 0, 'failed': 0, 'total_original_size': 0, 'total_compressed_size': 0}
                if total_files > 0:
                    with click.progressbar(length=total_files, label=f'  压缩 {subdir.name}', show_pos=True) as bar:
                        def update_progress(completed: int, total: int, filename: str, status: str = 'completed'):
                            if status == 'completed':
                                bar.update(1)

                        results = batch_processor.process_batch(
                            input_dir=subdir,
                            output_dir=subdir_output,
                            large_files=large_files,
                            small_files=small_files,
                            progress_callback=update_progress
                        )

                # 移动视频
                video_results = {'success': 0, 'failed': 0, 'total_size': 0}
                if video_files:
                    print(f"  移动 {len(video_files)} 个视频文件...")
                    video_results = batch_processor.move_video_files(
                        video_files=video_files,
                        output_dir=subdir_output
                    )

                # 判断是否成功
                subdir_success = results.get('failed', 0) == 0 and video_results.get('failed', 0) == 0

                if subdir_success:
                    # 删除原子目录
                    import shutil
                    shutil.rmtree(subdir)
                    print(f"  ✓ 完成，已删除原目录 {subdir.name}/")
                    total_results['subdirs_success'] += 1
                else:
                    print(f"  ✗ 存在失败，保留原目录 {subdir.name}/")
                    total_results['subdirs_failed'] += 1

                total_results['total_original_size'] += results.get('total_original_size', 0)
                total_results['total_compressed_size'] += results.get('total_compressed_size', 0)

            # 原地压缩一级图片
            if has_root_images:
                print(f"\n原地压缩一级图片 ({len(root_images)} 个)...")

                with click.progressbar(length=len(root_images), label='原地压缩', show_pos=True) as bar:
                    def update_inplace_progress(completed: int, total: int, filename: str, status: str = 'completed'):
                        if status == 'completed':
                            bar.update(1)

                    inplace_results = batch_processor.compress_inplace(
                        input_dir=input_dir,
                        min_size_mb=1.0,
                        progress_callback=update_inplace_progress
                    )

                total_results['inplace_success'] = inplace_results.get('success', 0)
                total_results['inplace_failed'] = inplace_results.get('failed', 0)
                total_results['total_original_size'] += inplace_results.get('total_original_size', 0)
                total_results['total_compressed_size'] += inplace_results.get('total_compressed_size', 0)

                if inplace_results.get('failed', 0) == 0:
                    print(f"  ✓ 一级图片压缩完成")
                else:
                    print(f"  ✗ 部分图片压缩失败")

            # 打印总结
            elapsed = datetime.now() - start_time
            total_original_mb = total_results['total_original_size'] / (1024 * 1024)
            total_compressed_mb = total_results['total_compressed_size'] / (1024 * 1024)
            saved_mb = total_original_mb - total_compressed_mb
            avg_ratio = total_compressed_mb / total_original_mb if total_original_mb > 0 else 0

            print("\n" + "=" * 50)
            print(f"处理完成")
            if has_subdirs:
                print(f"子目录处理:")
                print(f"  - 成功: {total_results['subdirs_success']} 个")
                print(f"  - 失败: {total_results['subdirs_failed']} 个")
            if has_root_images:
                print(f"一级图片原地压缩:")
                print(f"  - 成功: {total_results['inplace_success']} 个")
                print(f"  - 失败: {total_results['inplace_failed']} 个")
                print(f"  - 跳过(小文件): {inplace_results.get('skipped', 0)} 个")
            print(f"压缩统计:")
            print(f"  - 原始总大小: {total_original_mb:.2f} MB")
            print(f"  - 压缩后总大小: {total_compressed_mb:.2f} MB")
            print(f"  - 节省空间: {saved_mb:.2f} MB")
            print(f"  - 平均压缩比: {avg_ratio:.2%}")
            print(f"总用时: {elapsed}")
            print("=" * 50)

            logger.info("处理完成")

    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        logger.error(f"处理失败: {e}", exc_info=True)
        raise


def _process_single_directory(
    input_dir: Path,
    output: Path,
    quality: int,
    worker: int,
    force: bool,
    logger,
    pattern: str,
    atomic: bool
):
    """处理单个目录（原有逻辑）"""
    from src.core.compressor import Compressor
    from src.services.batch_processor import BatchProcessor
    from src.infrastructure.file_manager import FileManager

    start_time = datetime.now()

    # 确定输出目录
    if output is None:
        output = input_dir.parent / f"{input_dir.name}_compressed"
    output = output.resolve()

    logger.info(f"输出目录: {output}")

    # 初始化组件
    compressor = Compressor(quality=quality)
    file_manager = FileManager(atomic=atomic, backup=False)
    batch_processor = BatchProcessor(
        compressor=compressor,
        file_manager=file_manager,
        max_workers=worker
    )

    # 扫描文件
    logger.info("扫描文件...")
    large_files, small_files, video_files, scan_stats = batch_processor.scan_files(
        input_dir,
        pattern=pattern,
        min_size_mb=1.0,
        skip_existing=not force,
        output_dir=output
    )

    total_files = len(large_files) + len(small_files)
    total_video = len(video_files)
    if total_files == 0 and total_video == 0 and scan_stats['skipped'] == 0:
        logger.warning("没有找到需要处理的文件")
        return

    # 打印扫描结果
    print(f"\n扫描结果:")
    print(f"  - 图片总计: {scan_stats['total']} 个")
    print(f"  - 待处理: {total_files} 个 (大文件 {len(large_files)}, 小文件 {len(small_files)})")
    print(f"  - 已存在跳过: {scan_stats['skipped']} 个")
    if scan_stats['invalid'] > 0:
        print(f"  - 无效文件: {scan_stats['invalid']} 个")
    if total_video > 0:
        print(f"  - 视频文件: {total_video} 个")
    if scan_stats.get('video_skipped', 0) > 0:
        print(f"  - 视频已存在跳过: {scan_stats['video_skipped']} 个")

    if total_files == 0 and total_video == 0:
        logger.info("所有文件已处理完成，无需重复处理")
        return

    # 用户确认
    items_text = []
    if total_files > 0:
        items_text.append(f"{total_files} 个图片")
    if total_video > 0:
        items_text.append(f"{total_video} 个视频")
    print(f"\n即将处理 {' + '.join(items_text)}")
    print(f"质量参数: {quality}")
    print(f"输出目录: {output}")
    if not click.confirm("\n确认开始处理", default=True):
        logger.info("用户取消操作")
        return

    # 开始处理
    logger.info("开始处理...")

    # 使用 click.progressbar 显示进度
    with click.progressbar(length=total_files, label='正在压缩', show_pos=True) as bar:
        # 定义进度回调
        def update_progress(completed: int, total: int, filename: str, status: str = 'completed'):
            if status == 'completed':
                bar.update(1)

        # 处理文件
        results = batch_processor.process_batch(
            input_dir=input_dir,
            output_dir=output,
            large_files=large_files,
            small_files=small_files,
            progress_callback=update_progress
        )

    # 检查是否被中断
    if results.get('interrupted'):
        print("\n用户中断操作")
        return

    # 移动视频文件
    video_results = {'success': 0, 'failed': 0, 'total_size': 0}
    if video_files:
        print(f"\n正在移动 {len(video_files)} 个视频文件...")
        video_results = batch_processor.move_video_files(
            video_files=video_files,
            output_dir=output
        )

    # 打印结果
    elapsed = datetime.now() - start_time if 'start_time' in dir() else datetime.now() - datetime.now()
    total_original_mb = results['total_original_size'] / (1024 * 1024)
    total_compressed_mb = results['total_compressed_size'] / (1024 * 1024)
    video_size_mb = video_results['total_size'] / (1024 * 1024)
    saved_mb = total_original_mb - total_compressed_mb
    avg_ratio = total_compressed_mb / total_original_mb if total_original_mb > 0 else 0

    print("\n" + "=" * 50)
    print(f"处理完成")
    print(f"图片处理:")
    print(f"  - 总文件数: {results['total']}")
    print(f"  - 压缩成功: {results['success']}")
    print(f"  - 小文件复制: {results.get('copied', 0)}")
    print(f"  - 失败: {results['failed']}")
    if video_files:
        print(f"视频处理:")
        print(f"  - 移动成功: {video_results['success']}")
        print(f"  - 失败: {video_results['failed']}")
        print(f"  - 视频大小: {video_size_mb:.2f} MB")
    print(f"压缩统计:")
    print(f"  - 原始总大小: {total_original_mb:.2f} MB")
    print(f"  - 压缩后总大小: {total_compressed_mb:.2f} MB")
    print(f"  - 节省空间: {saved_mb:.2f} MB")
    print(f"  - 平均压缩比: {avg_ratio:.2%}")
    print(f"总用时: {elapsed}")
    print("=" * 50)

    # 清理临时文件
    temp_count = file_manager.cleanup_temp_files(output)
    if temp_count > 0:
        logger.info(f"清理了 {temp_count} 个临时文件")

    # 删除原文件夹
    if results['failed'] == 0 and video_results['failed'] == 0:
        import shutil
        logger.info(f"删除原文件夹: {input_dir}")
        shutil.rmtree(input_dir)
        print(f"\n已删除原文件夹: {input_dir}")
    else:
        logger.warning("存在处理失败的文件，保留原文件夹")

    logger.info("处理完成")


if __name__ == '__main__':
    compress()
