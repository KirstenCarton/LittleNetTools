import tkinter as tk
from tkinter import filedialog
import contextlib
import os
import queue
import requests
import sys
import threading
import time

# 工具函数，用于修改目录，可以复用
@contextlib.contextmanager
def chdir(path):
    this_dir = os.getcwd()          # this_dir就是获取当前目录
    os.chdir(path)
    try:                            # 转到执行目录执行程序
        yield
    finally:                        # 最后还是会回到原本的目录
        os.chdir(this_dir)


class DirscanGUI:
    # 目前这些都属于类的属性（静态还是动态？？）
    FILTERD = [".jpg", ".png", ".gif", ".css", ".svg", ".js", ".py"]
    TARGET = "http://rarara.cn/"
    THREADS = 10
    PATH = 'D:\\Py0401\\try1st\\A-Tool-HomeWork\\admin'  # 似乎得是本地的路径

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Dirscan Tool")
        self.answers = queue.Queue()  # 这answers是个队列啊我去。。总觉得队列会很有问题
        self.web_paths = queue.Queue()

        # 添加 PATH Label 和输入框
        self.path_label = tk.Label(self.window, text="PATH:")
        self.path_label.grid(row=0, column=0, padx=5, pady=5)
        self.path_entry = tk.Entry(self.window, width=50)
        self.path_entry.grid(row=0, column=1, padx=5, pady=5)

        # 添加浏览按钮
        self.browse_button = tk.Button(self.window, text="Browse", command=self.browse_path)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

        # 添加运行按钮
        self.run_button = tk.Button(self.window, text="Run", command=self.run_dirscan)
        self.run_button.grid(row=1, column=1, padx=5, pady=5)

        self.window.mainloop()

    # 浏览文件夹并将路径显示在输入框中
    def browse_path(self):
        path = filedialog.askdirectory()
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, path)

    # 运行Dirscan
    def run_dirscan(self):
        # 获取输入框中的路径
        path = self.path_entry.get()
        # 如果路径为空，弹出提示框
        if not path:
            tk.messagebox.showwarning("Warning", "Please select a directory.")
            return
        # 如果路径存在，运行Dirscan
        else:
            # 修改目录
            with chdir(path):
                self.gather_paths()
            self.run()
            tk.messagebox.showinfo("Information", "Done.")

    # 收集目录信息的函数
    def gather_paths(self):
        path = os.getcwd()
        print(path)
        for root, subpath, files in os.walk(path):  # 修改PATH为path
            for fname in files:
                if os.path.splitext(fname)[1] in self.FILTERD:  # 若后缀符合filter就跳过
                    continue
                relative_path = os.path.relpath(path)  # 获取相对路径
                # print(relative_path)
                try:  # 为了解决写操作没有发生的问题，尝试判断当前用户是否具有写的权限
                    if os.access(path, os.W_OK):  # os.access(path, mode) 判断当前用户是否可写
                        with open("D:\\Py0401\\try1st\\A-Tool-HomeWork\\wapper.txt", 'a') as f:
                            if fname != 'wrapper.txt':  # 排除文件本身
                                f.write(relative_path + "\n")
                        print("writing " + path)
                    else:
                        print("you cannot write")
                        continue
                except Exception as e:
                    print("no writed" + e)
                finally:
                    f.close()
                path = os.path.join(root, fname)

                if path.startswith('.'):  # 如果是以.开头的文件，就是隐藏文件，去掉.  似乎是这里的原因，导致没法使用相对路径（好像不是这个原因）
                    path = path[1:]
                # 入队列
                self.web_paths.put(relative_path)

    # 测试是否能将本地路径文件和在线网站目录匹配
    def remote_test(self):
        while not self.web_paths.empty():
            path = self.web_paths.get()
            url = f'{self.TARGET}{path}'
            time.sleep(0.1)

            req = requests.get(url)
            try:
                if req.status_code == 200:
                    self.answers.put(url)
                    sys.stdout.write("\n[+]")
                    print(url)
            except Exception as e:
                raise e
            sys.stdout.flush()

        with open('url-dir.txt', 'a') as ff, open('url-dir.txt', 'r') as f:
            f.seek(0)  # 将文件指针移到文件开头
            lines = [item.strip() for item in f.readlines()]
            while not self.answers.empty():
                current_line = self.answers.get()  # 需要变量保存一下get的值
                if current_line.strip() not in lines:
                    # lines.append(answers.get())
                    ff.write(f'{current_line}\n')

    # 用于线程管理的函数
    def run(self):
        mythreads = list()
        for i in range(self.THREADS):
            print(f'Spawning thread {i}')
            t = threading.Thread(target=self.remote_test)
            mythreads.append(t)
            t.start()
        for thread in mythreads:
            thread.join()


if __name__ == '__main__':
    DirscanGUI()
