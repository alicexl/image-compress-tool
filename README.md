# 图片压缩工具

批量 JPEG 图片压缩工具，支持并发处理、智能跳过、进度显示、视频文件复制。

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
# 基本使用
python run.py <图片目录>

# 指定质量和并发数
python run.py D:/photos -q 80 -w 4

# 指定输出目录
python run.py D:/photos -o D:/photos_compressed

# 强制重新处理
python run.py D:/photos -f

# 路径含空格或中文时，用引号包裹
python run.py "D:/photos/我的 相册" -q 80
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `<目录>` | 必需 | 图片所在目录 |
| `-q, --quality` | 75 | 压缩质量 (1-100) |
| `-w, --worker` | 4 | 并发数 (1-8) |
| `-o, --output` | `<输入目录>_compressed` | 输出目录 |
| `-f, --force` | False | 强制覆盖已存在文件 |

## 功能

- **智能跳过**: 自动跳过已存在的有效文件
- **小文件复制**: <1MB 的文件直接复制
- **视频文件**: 自动复制视频文件到输出目录
- **并发处理**: 多线程加速
- **进度显示**: 实时进度条
- **优雅中断**: Ctrl+C 安全退出

## 支持格式

| 类型 | 扩展名 |
|------|--------|
| 图片 | `.jpg`, `.jpeg` |
| 视频 | `.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.mpeg`, `.mpg`, `.3gp` |

## 注意

- 建议先备份原始文件
- 推荐质量范围: 70-85
- 并发数建议设为 CPU 核心数
- 视频文件原样复制，不进行压缩
