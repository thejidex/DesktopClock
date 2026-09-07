# Desktop Clock

Desktop Clock 是一个面向 Windows 的轻量桌面时钟程序，使用 Python、Tkinter 和 Pillow 开发。程序支持桌面无边框模式、多显示器真正全屏、预置主题和自定义壁纸，并提供简单的设置窗口。

当前版本：Desktop Clock v1.1.0

## 功能特性

- 实时显示本机时间，默认格式为 `HH:MM:SS`，也可隐藏秒并显示为 `HH:MM`
- 显示当前日期和星期
- 在同一个主窗口中切换时钟、倒计时、秒表和闹钟模式
- 倒计时支持设置时、分、秒，以及开始、暂停、继续和重置
- 秒表支持开始、暂停、继续和重置，并使用单调时钟避免刷新误差
- 支持一个每天重复的 `HH:MM` 闹钟，并保存启用状态和时间
- 根据窗口大小自动调整时间和日期字体
- 内置 Dark、Light、OLED 三种主题
- 支持 PNG、JPG、JPEG 和 WebP 自定义壁纸
- 壁纸等比例 Cover 缩放、居中裁剪
- 可调节 0%～70% 的壁纸暗化程度
- 可分别控制日期和星期是否显示
- Canvas 文字叠加，时间和日期直接显示在壁纸上
- 桌面无边框模式，并保留 Windows 任务栏应用图标和原生最小化行为
- 桌面模式下支持鼠标拖动窗口和跨显示器移动
- 可选始终置顶
- 在窗口当前所在显示器进入真正全屏
- 支持 F11、Esc、鼠标双击切换或退出全屏
- 点击 Windows 最大化按钮时转换为真正全屏
- Ctrl+S 或鼠标右键打开、关闭同一个设置窗口
- 设置窗口自动定位到主时钟所在显示器，并保持在该显示器工作区内
- 自动保存主题、壁纸和窗口相关设置
- 自动恢复普通窗口或桌面模式下的位置和大小
- 保存的位置不可见时，自动将窗口移回当前可用显示器

## 快捷键和鼠标操作

| 操作 | 功能 |
| --- | --- |
| `Ctrl+S` | 打开或关闭设置窗口 |
| `Ctrl+1` | 切换到 Dark 主题 |
| `Ctrl+2` | 切换到 Light 主题 |
| `Ctrl+3` | 切换到 OLED 主题 |
| `Ctrl+Shift+1` | 切换到时钟模式 |
| `Ctrl+Shift+2` | 切换到倒计时模式 |
| `Ctrl+Shift+3` | 切换到秒表模式 |
| `Ctrl+Shift+4` | 切换到闹钟模式 |
| `F11` | 在当前显示器切换真正全屏 |
| `Esc` | 退出真正全屏；非全屏时不执行操作 |
| 鼠标左键双击时钟区域 | 切换真正全屏 |
| 鼠标右键单击时钟区域 | 打开或关闭设置窗口 |
| 鼠标左键拖动时钟区域 | 在桌面模式下移动窗口 |

## 运行方式

请在项目根目录打开 PowerShell。

### 1. 创建虚拟环境

```powershell
py -3 -m venv .venv
```

### 2. 安装运行依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

### 3. 启动程序

```powershell
.\.venv\Scripts\python.exe .\main.py
```

程序每次启动时保持普通窗口或已保存的桌面模式，不会恢复为真正全屏状态。

## 时间工具操作

使用 `Ctrl+S` 打开设置，在“功能”页选择主窗口模式。时钟模式仍保持简洁，只显示时间以及已启用的日期和星期；其它模式会在主窗口底部显示必要控件。

- 倒计时：输入小时、分钟和秒后点击“开始”。运行时可暂停、继续或重置；归零后自动停止，只响铃并提示一次。
- 秒表：点击“开始”计时，可暂停、继续或重置。本版本不包含毫秒、圈数和历史记录。
- 闹钟：输入 `0～23` 小时和 `0～59` 分钟后启用。闹钟每天在指定时间提示一次；关闭后不会触发。
- 显示秒：在设置的“外观与显示”页即时开启或关闭，选择会自动保存。

## 构建 EXE

先安装开发依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
```

然后在项目根目录运行构建脚本：

```powershell
.\build.ps1
```

构建脚本使用项目自己的 `.venv\Scripts\python.exe` 调用 PyInstaller，并生成单文件、无控制台窗口的 Windows 程序。
单文件程序不依赖固定盘符。运行时会在 EXE 当前工作目录创建一个临时的
`_MEI...` 资源目录，正常退出后会自动删除；请把 EXE 放在桌面、下载目录
或其它当前用户可写的文件夹中运行。

构建成功后的文件位于：

```text
dist\DesktopClock.exe
```

## 用户数据

默认应用数据目录为：

```text
%LOCALAPPDATA%\DesktopClock
```

默认配置文件位于：

```text
%LOCALAPPDATA%\DesktopClock\config.json
```

如需把数据保存到其它位置，可以设置 `DESKTOP_CLOCK_DATA_DIR` 环境变量。下面的 PowerShell 示例只对当前终端会话生效：

```powershell
$env:DESKTOP_CLOCK_DATA_DIR = "D:\DesktopClockData"
.\.venv\Scripts\python.exe .\main.py
```

运行打包后的程序时也使用同一个环境变量。需要长期使用自定义目录时，可以在 Windows 用户环境变量中添加 `DESKTOP_CLOCK_DATA_DIR`。

配置文件保存以下内容：

- 当前主题
- 壁纸原始文件的完整路径
- 壁纸暗化程度
- 日期和星期显示状态
- 是否显示秒
- 闹钟时间和启用状态
- 桌面模式状态
- 始终置顶状态
- 普通窗口或桌面模式下的位置和大小

程序不会复制用户选择的壁纸，也不会保存真正全屏状态。全屏默认不会强制置顶，切换到其它软件时不会被时钟遮挡。如果保存的壁纸路径失效，程序会安静地回退到当前主题的纯色背景，其它设置仍然有效。

当前数据目录中没有配置时，程序会尝试从旧的 `D:\DesktopClockData\config.json` 或 `%APPDATA%\DesktopClock\config.json` 迁移已有配置，但不会删除旧文件。旧 D 盘路径只用于兼容历史版本，不再是默认目录；没有 D 盘的电脑不会因此报错。

## 项目结构

| 路径 | 作用 |
| --- | --- |
| `main.py` | 程序入口；负责时钟、Canvas、窗口状态、快捷键和 Win32 多显示器逻辑 |
| `time_tools.py` | 使用 `time.monotonic()` 实现倒计时和秒表状态计算 |
| `settings.py` | 使用 Tkinter `Toplevel` 创建和管理设置窗口 |
| `themes.py` | 保存 Dark、Light、OLED 主题定义 |
| `wallpaper.py` | 使用 Pillow 加载、缩放、裁剪壁纸并添加暗色遮罩 |
| `config.py` | 读取、校验、迁移和保存配置 |
| `assets/` | 保存应用图标等运行时资源 |
| `build.ps1` | Windows PyInstaller 自动构建脚本 |
| `requirements.txt` | 程序运行依赖 |
| `requirements-dev.txt` | EXE 构建依赖 |

## 技术栈

- Python 3
- Tkinter
- Pillow
- Win32 API（通过 `ctypes` 调用）
- PyInstaller

## 系统要求

- Windows 操作系统
- 从源码运行时需要 Python 3 和可用的 Tkinter
- 默认需要当前 Windows 用户的 `%LOCALAPPDATA%` 目录可写

当前代码直接使用 Windows Win32 API，不声明支持 Linux 或 macOS。发布版不要求电脑存在 `D:` 盘。

## 版本

Desktop Clock v1.1.0
