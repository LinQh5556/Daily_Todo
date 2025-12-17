import tkinter as tk
from tkinter import messagebox, filedialog, Menu, Scrollbar
import json
import os
import sys
import winreg
import threading
import ctypes # 用于系统API调用
from datetime import datetime

# 依赖库
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageTk, ImageOps 

# ================= 配置区域 =================
APP_TITLE = "Daily_List"
WINDOW_WIDTH = 450
WINDOW_HEIGHT = 720 # 稍微加高一点容纳滚动条
WINDOW_SIZE = f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
CARD_ALPHA = 180 

DATA_FILE = "todo_data_final.json"
ICON_FILE = "app_icon.ico" # 如果目录下有这个图标文件，会自动加载
DEFAULT_TIMES = ["11:30", "17:30"]

# 【新增】尝试开启 Windows 高DPI感知，解决模糊问题
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except: pass
# ===========================================

class DailyTodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)

        # 【新增】设置程序图标
        if os.path.exists(ICON_FILE):
            try: self.root.iconbitmap(ICON_FILE)
            except: pass

        # 数据初始化
        self.tasks = []
        self.reminder_times = []
        self.bg_image_path = ""
        self.auto_start_var = tk.BooleanVar()
        self.last_alert_signature = (None, None)

        self.root.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)
        self.load_data()

        # Canvas 布局
        self.canvas = tk.Canvas(self.root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.refresh_background_image()
        self.setup_widgets()
        
        self.refresh_task_list()
        self.refresh_time_list()
        self.check_reminder_loop()

    def refresh_background_image(self):
        if self.bg_image_path and os.path.exists(self.bg_image_path):
            try:
                base_img = Image.open(self.bg_image_path).convert("RGBA")
                base_img = ImageOps.fit(base_img, (WINDOW_WIDTH, WINDOW_HEIGHT), method=Image.Resampling.LANCZOS)
            except:
                base_img = Image.new("RGBA", (WINDOW_WIDTH, WINDOW_HEIGHT), "#333333")
        else:
            base_img = Image.new("RGBA", (WINDOW_WIDTH, WINDOW_HEIGHT), "#333333")

        # 创建半透明遮罩
        overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # 调整了卡片高度以适应滚动条
        draw.rectangle((20, 20, WINDOW_WIDTH-20, 390), fill=(255, 255, 255, CARD_ALPHA)) # 任务区
        draw.rectangle((20, 410, WINDOW_WIDTH-20, 700), fill=(255, 255, 255, CARD_ALPHA)) # 设置区

        combined_img = Image.alpha_composite(base_img, overlay)
        self.tk_image = ImageTk.PhotoImage(combined_img)
        self.canvas.delete("bg") 
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw", tag="bg")
        self.canvas.tag_lower("bg")

    def setup_widgets(self):
        # 标题
        self.canvas.create_text(40, 50, text="待办任务", font=("微软雅黑", 14, "bold"), anchor="w", fill="#333")
        self.canvas.create_text(40, 440, text="提醒设置", font=("微软雅黑", 14, "bold"), anchor="w", fill="#333")

        # --- 任务输入 ---
        self.task_entry = tk.Entry(self.root, font=("微软雅黑", 10), bd=1, relief="solid")
        self.task_entry.bind('<Return>', lambda e: self.add_task())
        self.canvas.create_window(35, 80, window=self.task_entry, width=300, height=30, anchor="nw")
        
        add_btn = tk.Button(self.root, text="添加", bg="#0078d7", fg="white", relief="flat", command=self.add_task)
        self.canvas.create_window(345, 80, window=add_btn, width=60, height=30, anchor="nw")

        # --- 任务列表 + 滚动条 ---
        # 创建一个 Frame 来容纳 Listbox 和 Scrollbar，方便管理
        task_frame = tk.Frame(self.root, bg="white", bd=0)
        # 将 Frame 放到 Canvas 上
        self.canvas.create_window(35, 120, window=task_frame, width=370, height=210, anchor="nw")
        
        self.task_scrollbar = Scrollbar(task_frame)
        self.task_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.task_listbox = tk.Listbox(task_frame, font=("微软雅黑", 11), bg="#ffffff", bd=0, 
                                       highlightthickness=0, yscrollcommand=self.task_scrollbar.set)
        self.task_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.task_scrollbar.config(command=self.task_listbox.yview)

        # 绑定事件
        self.task_listbox.bind('<Double-1>', lambda event: self.delete_task())
        self.task_listbox.bind('<Button-3>', lambda event: self.show_context_menu(event, "task"))

        # 删除按钮
        del_task_btn = tk.Button(self.root, text="删除选中任务", font=("微软雅黑", 9), command=self.delete_task)
        self.canvas.create_window(320, 340, window=del_task_btn, anchor="nw")

        # --- 时间列表 + 滚动条 ---
        time_frame = tk.Frame(self.root, bg="white", bd=0)
        self.canvas.create_window(35, 480, window=time_frame, width=180, height=140, anchor="nw")
        
        self.time_scrollbar = Scrollbar(time_frame)
        self.time_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.time_listbox = tk.Listbox(time_frame, font=("Consolas", 11), bg="#ffffff", bd=0, 
                                       highlightthickness=0, yscrollcommand=self.time_scrollbar.set)
        self.time_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.time_scrollbar.config(command=self.time_listbox.yview)

        # 绑定事件
        self.time_listbox.bind('<Double-1>', lambda event: self.delete_time())
        self.time_listbox.bind('<Button-3>', lambda event: self.show_context_menu(event, "time"))

        # --- 设置操作 ---
        self.time_entry = tk.Entry(self.root, width=8, font=("Consolas", 11))
        self.canvas.create_window(240, 480, window=self.time_entry, anchor="nw")
        
        add_time_btn = tk.Button(self.root, text="添加时间", command=self.add_time, font=("微软雅黑", 9))
        self.canvas.create_window(330, 477, window=add_time_btn, anchor="nw")

        self.canvas.create_text(35, 630, text="* 双击或右键可删除时间", fill="#888", font=("微软雅黑", 8), anchor="nw")

        # --- 换背景 ---
        bg_btn = tk.Button(self.root, text="更换背景图", command=self.choose_bg_image, bg="#ff9800", fg="white", font=("微软雅黑", 9, "bold"))
        self.canvas.create_window(240, 530, window=bg_btn, width=150, anchor="nw")

        # --- 开机自启 ---
        self.auto_start_var.set(self.check_auto_start_status())
        chk = tk.Checkbutton(self.root, text="开机自启动", variable=self.auto_start_var, command=self.toggle_auto_start, bg="white") 
        self.canvas.create_window(320, 660, window=chk, anchor="nw")

        # 右键菜单
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="删除", command=self.delete_from_menu)

    # ================= 逻辑处理 =================
    def show_context_menu(self, event, list_type):
        self.current_menu_target = list_type
        widget = event.widget
        try:
            widget.selection_clear(0, tk.END)
            widget.selection_set(widget.nearest(event.y))
            self.context_menu.post(event.x_root, event.y_root)
        except: pass

    def delete_from_menu(self):
        if self.current_menu_target == "task": self.delete_task()
        elif self.current_menu_target == "time": self.delete_time()

    def choose_bg_image(self):
        path = filedialog.askopenfilename(title="选择背景", filetypes=[("图片", "*.jpg;*.png;*.jpeg")])
        if path:
            self.bg_image_path = path
            self.save_data()
            self.refresh_background_image()

    def add_task(self):
        t = self.task_entry.get().strip()
        if t:
            self.tasks.append(t)
            self.task_entry.delete(0, tk.END)
            self.save_data()
            self.refresh_task_list()

    def delete_task(self):
        try:
            index = self.task_listbox.curselection()[0]
            del self.tasks[index]
            self.save_data()
            self.refresh_task_list()
        except IndexError: pass 

    def refresh_task_list(self):
        self.task_listbox.delete(0, tk.END)
        for i, t in enumerate(self.tasks):
            self.task_listbox.insert(tk.END, f" {i+1}. {t}")

    def add_time(self):
        t = self.time_entry.get().strip()
        try:
            ft = datetime.strptime(t, "%H:%M").strftime("%H:%M")
            if ft not in self.reminder_times:
                self.reminder_times.append(ft)
                self.reminder_times.sort()
                self.save_data()
                self.refresh_time_list()
            else: messagebox.showinfo("提示", "该时间已存在")
        except: messagebox.showerror("错误", "格式应为 HH:MM")

    def delete_time(self):
        try:
            index = self.time_listbox.curselection()[0]
            del self.reminder_times[index]
            self.save_data()
            self.refresh_time_list()
        except IndexError: pass

    def refresh_time_list(self):
        self.time_listbox.delete(0, tk.END)
        for t in self.reminder_times:
            self.time_listbox.insert(tk.END, f" ⏰ {t}")

    def save_data(self):
        data = {"tasks": self.tasks, "reminder_times": self.reminder_times, "bg_image_path": self.bg_image_path}
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
        except: pass

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    self.tasks = d.get("tasks", [])
                    self.reminder_times = d.get("reminder_times", DEFAULT_TIMES)
                    self.bg_image_path = d.get("bg_image_path", "")
            except: self.tasks, self.reminder_times = [], DEFAULT_TIMES
        else: self.tasks, self.reminder_times = [], DEFAULT_TIMES

    def check_reminder_loop(self):
        now = datetime.now()
        ct, cd = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
        if ct in self.reminder_times and self.tasks:
            if self.last_alert_signature != (cd, ct):
                self.last_alert_signature = (cd, ct)
                self.show_window()
                msg = "\n".join([f"{i+1}. {t}" for i, t in enumerate(self.tasks)])
                messagebox.showwarning("提醒", f"时间到 {ct}！\n未完成：\n{msg}")
        self.root.after(5000, self.check_reminder_loop)

    def minimize_to_tray(self):
        self.root.withdraw()
        threading.Thread(target=self.create_tray_icon, daemon=True).start()

    def create_tray_icon(self):
        img = Image.new('RGB', (64, 64), (0, 120, 215))
        d = ImageDraw.Draw(img)
        d.rectangle((20, 20, 44, 44), fill="white")
        # 如果有本地图标文件，优先使用本地图标
        if os.path.exists(ICON_FILE):
            try: img = Image.open(ICON_FILE)
            except: pass
            
        menu = (item('显示', self.show_window_from_tray), item('退出', self.quit_app))
        self.icon = pystray.Icon("todo", img, "每日清单", menu)
        self.icon.run()

    def show_window_from_tray(self, icon=None, item=None):
        self.icon.stop()
        self.root.after(0, self.show_window)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()

    def quit_app(self, icon=None, item=None):
        self.icon.stop()
        self.root.quit()
        sys.exit()

    def get_exe_path(self):
        return sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)

    def check_auto_start_status(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_TITLE)
            winreg.CloseKey(key)
            return True
        except: return False

    def toggle_auto_start(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            if self.auto_start_var.get():
                winreg.SetValueEx(key, APP_TITLE, 0, winreg.REG_SZ, self.get_exe_path())
            else:
                try: winreg.DeleteValue(key, APP_TITLE)
                except: pass
            winreg.CloseKey(key)
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.auto_start_var.set(not self.auto_start_var.get())

if __name__ == "__main__":
    root = tk.Tk()
    app = DailyTodoApp(root)
    root.mainloop()
