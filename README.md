# lite-get

一个轻量级的媒体下载工具，支持从 B 站、YouTube 等平台下载视频、音频和字幕，目前已实现对 M3U8 链接的下载。

> **lite-get** 是由 [you-get](https://github.com/soimort/you-get) 精简重构而来的命令行下载器，保留核心下载能力，代码更轻量、更易维护。

## 功能特性

- ✅ **M3U8 流媒体下载** — 通过 FFmpeg 直接下载 M3U8 视频流，输出 MP4 格式
- 🚧 **B 站下载** — 下载视频/音频/字幕
- 🚧 **YouTube 下载** — 下载视频/音频/字幕
- 🚧 **网易云音乐下载** — 下载音频
- ✅ **FFmpeg 工具集** — 内置视频合并、转封装、流下载等工具函数
- ✅ **跨平台文件名处理** — 自动适配 Linux / macOS / Windows 的文件名合法性

## 环境要求

- **Python 3.x** (不支持 Python 2)
- **FFmpeg** 或 **avconv** (系统需安装其中之一)

> 如需下载 B 站 / YouTube 等平台的视频，还需安装 [you-get](https://github.com/soimort/you-get) Python 包。

## 安装

### 方式一：从源码安装

```bash
git clone <repo-url>
cd lite-get
pip install .
```

安装后可直接使用 `lite-get` 命令。

### 方式二：直接运行

无需安装，通过项目自带的 Shell 脚本直接运行：

```bash
cd lite-get
./lite-get [OPTION]... URL...
```

## 使用方法

### 基本语法

```bash
lite-get [OPTION]... URL...
```

### 下载 M3U8 视频

```bash
# 下载 M3U8 视频，默认输出文件名为 m3u8file.mp4
lite-get -m "https://example.com/path/to/video.m3u8"

# 指定输出文件
lite-get -m -O my_video "https://example.com/path/to/video.m3u8"

# 指定输出目录
lite-get -m -o ./downloads "https://example.com/path/to/video.m3u8"
```


### 命令行选项

| 选项 | 说明 |
|------|------|
| `-V`, `--version` | 打印版本号并退出 |
| `-h`, `--help` | 打印帮助信息并退出 |
| `-m`, `--m3u8` | 以 M3U8 模式下载视频流 |
| `-o DIR`, `--output-dir DIR` | 指定输出目录 (默认: 当前目录 `.`) |
| `-O FILE`, `--output-filename FILE` | 指定输出文件名 |
| `-i`, `--info` | 打印视频信息 (不下载) |
| `-u`, `--url` | 打印视频 URL 信息 |
| `-d`, `--debug` | 开启调试模式，显示详细错误堆栈 |

### 示例

```bash
# 下载 M3U8 视频到指定目录和文件名
lite-get -m -o ./videos -O episode1 "https://example.com/stream.m3u8"

# 查看版本号
lite-get -V

# 开启调试模式排查问题
lite-get -d -m "https://example.com/stream.m3u8"
```

## 项目结构

```
lite-get
├── lite-get              # Shell 启动脚本 (可直接执行)
├── setup.py              # setuptools 安装配置
├── LICENSE.txt           # MIT 许可证
├── src/
│   ├── lite_get/         # 主源码包
│   │   ├── __init__.py
│   │   ├── __main__.py       # 程序入口
│   │   ├── common.py         # CLI 参数解析、下载调度核心逻辑
│   │   ├── version.py        # 版本号定义
│   │   ├── processor/
│   │   │   └── ffmpeg.py     # FFmpeg 检测、流下载、视频合并/转封装
│   │   └── util/
│   │       ├── fs.py         # 跨平台文件名合法化处理
│   │       ├── log.py        # ANSI 彩色终端日志输出
│   │       ├── os.py         # 操作系统检测 (Linux/macOS/Windows/WSL)
│   │       ├── strings.py    # 正则匹配、字符串处理工具
│   │       └── url.py        # URL 路由分发、站点→提取器映射、HTTP 工具
│   └── test/                 # 单元测试
└── build/                    # 构建输出目录
```

## 依赖说明

本项目核心功能仅依赖 **Python 3 标准库** 和系统安装的 **FFmpeg**，无需额外安装 Python 包即可使用 M3U8 下载功能。


## 许可证

[MIT](LICENSE.txt) © 2026 kairon57
