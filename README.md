# 🌟 Glassy Todo List | 每日清单 (磨砂玻璃版)

> 一个高颜值、支持自定义背景与透明磨砂效果的 Windows 桌面待办事项应用。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-0078d7)

**Glassy Todo List** 是一个基于 Python `Tkinter` 开发的轻量级任务管理工具。

## 🛠️ 安装与使用 (Installation)

### 方式一：直接运行源码

确保你的电脑上安装了 Python 3.x。

1.  **克隆仓库**
    ```bash
    git clone https://github.com/LinQh5556/Daily_Todo
    cd Daily_Todo
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```
    *(如果没有 requirements.txt，请运行: `pip install pystray Pillow`)*

3.  **运行程序**
    ```bash
    python main.py
    ```

### 方式二：打包为 EXE (推荐)

如果你想生成独立的 `.exe` 文件以便分享或自启：

1.  安装打包工具：
    ```bash
    pip install pyinstaller
    ```

2.  执行打包命令（包含图标）：
    ```bash
    pyinstaller --noconsole --onefile --name="每日清单" --icon=app_icon.ico main.py
    ```
    *(注：请确保目录下有 `app_icon.ico` 图标文件，如果没有，去掉 `--icon` 参数即可)*

3.  在 `dist` 文件夹中找到 `每日清单.exe` 即可使用。

## 📂 项目结构

```text
daily-todo-list/
├── main.py              # 主程序代码
├── todo_data_final.json # 数据存储文件 (自动生成)
├── app_icon.ico         # 程序图标
├── requirements.txt     # 依赖库列表
└── README.md            # 项目说明文档
```

## 🤝 贡献 (Contributing)
欢迎提交 Issue 或 Pull Request 来改进这个小工具！
如果你有更好的 UI 配色方案或新功能建议，请随时告诉我。

## 📄 开源协议 (License)
本项目基于 MIT License 开源，你可以免费用于任何用途。





