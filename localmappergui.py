import contextlib
import os
import time
import tkinter as tk
import threading
import queue

import requests

from localmapper import FILTERD, web_paths, answers
FILTERD = [".jpg", ".png", ".gif", ".css", ".svg", ".js", ".py"]
TARGET = "http://rarara.cn/"
THREADS = 10
PATH = 'D:\\Py0401\\try1st\\A-Tool-HomeWork\\admin'       # 似乎得是本地的路径


# 工具函数
@contextlib.contextmanager
def chdir(path):
    this_dir = os.getcwd()  # this_dir就是获取当前目录
    os.chdir(path)
    try:                    # 转到执行目录执行程序
        yield
    finally:                # 最后还是会回到原本的目录
        os.chdir(this_dir)

class LocalMapperGUI:
    def __init__(self, master):
        self.master = master
        master.title("Local Mapper")

        # create labels and entry for target url and path
        self.url_label = tk.Label(master, text="Target URL:")
        self.url_label.grid(row=0, column=0)

        self.url_entry = tk.Entry(master, width=50)
        self.url_entry.insert(0, "http://rarara.cn/")
        self.url_entry.grid(row=0, column=1)

        self.path_label = tk.Label(master, text="Path:")
        self.path_label.grid(row=1, column=0)

        self.path_entry = tk.Entry(master, width=50)
        self.path_entry.insert(0, "D:\\Py0401\\try1st\\A-Tool-HomeWork\\admin")
        self.path_entry.grid(row=1, column=1)

        # create button to start mapping
        self.map_button = tk.Button(master, text="Start Mapping", command=self.start_mapping)
        self.map_button.grid(row=2, column=1)

        # create label for displaying status
        self.status_label = tk.Label(master, text="Status: Ready")
        self.status_label.grid(row=3, column=1)

        # create text widget for displaying results
        self.results_text = tk.Text(master, height=20, width=80)
        self.results_text.grid(row=4, column=0, columnspan=2)

        # create queue for storing results
        self.answers = queue.Queue()

    def start_mapping(self):
        # disable mapping button and clear previous results
        self.map_button.config(state=tk.DISABLED)
        self.results_text.delete("1.0", tk.END)
        self.status_label.config(text="Status: Mapping...")

        # start mapping in a new thread
        with chdir(self.path_entry.get()):
            mapping_thread = threading.Thread(target=self.map_local_files)
            mapping_thread.start()

        # check if mapping thread has finished every second
        self.master.after(1000, self.check_mapping_status, mapping_thread)

    def map_local_files(self):
        # get target url and path from entry fields
        target_url = self.url_entry.get()
        path = self.path_entry.get()
        # chdir(path)??修改目录？？
        # gather local file paths
        for root, subpath, files in os.walk(path):
            for fname in files:
                if os.path.splitext(fname)[1] in FILTERD:       # TODO 这个变量有问题
                    continue
                relative_path = os.path.relpath(path)
                try:
                    if os.access(path, os.W_OK):
                        with open("D:\\Py0401\\try1st\\A-Tool-HomeWork\\wapper.txt", 'a') as f:
                            if fname != 'wrapper.txt':
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

                if path.startswith('.'):
                    path = path[1:]
                web_paths.put(relative_path)        # 这个变量有问题

        # start remote testing
        while not web_paths.empty():
            path = web_paths.get()
            url = f'{target_url}/{path}'
            time.sleep(0.1)

            req = requests.get(url)
            try:
                if req.status_code == 200:
                    answers.put(url)
                    print("[+] " + url)
            except Exception as e:
                raise e

        # write results to file and display on GUI
        with open('url-dir.txt', 'a') as ff, open('url-dir.txt', 'r') as f:
            f.seek(0)
            lines = [item.strip() for item in f.readlines()]
            while not answers.empty():
                current_line = answers.get()
                if current_line.strip() not in lines:
                    ff.write(f'{current_line}')

        # write results to file and display on GUI
        with open('url-dir.txt', 'a') as ff, open('url-dir.txt', 'r') as f:
            f.seek(0)
            lines = [item.strip() for item in f.readlines()]
            while not answers.empty():
                current_line = answers.get()
                if current_line.strip() not in lines:
                    ff.write(f'{current_line}\n')
                self.results_text.insert(tk.END, current_line + "\n")

        # update status label and enable mapping button
        self.status_label.config(text="Status: Done")
        self.map_button.config(state=tk.NORMAL)

    def check_mapping_status(self, mapping_thread):
        if mapping_thread.is_alive():
            self.master.after(1000, self.check_mapping_status, mapping_thread)
        else:
            self.status_label.config(text="Status: Done")
            self.map_button.config(state=tk.NORMAL)


if __name__ == '__main__':
    root = tk.Tk()
    local_mapper_gui = LocalMapperGUI(root)
    root.mainloop()
