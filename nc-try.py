import argparse
import os
import socket
import shlex
import subprocess
import sys
import textwrap
import threading


class NetCat:
    # 将常量定义为类变量、模块变量 魔术数值指硬编码的数值、字符串，会出现在代码的多个地方
    BUFFER_SIZE = 4096
    ERROR_MESSAGE = "An error occurred"

    # 有一个想法就是，各个方法组合一个基类，然后对组合类进行文件上传和下载
    # 降低代码耦合度的比较好的方法就是：将实例传递给工具类
    def __init__(self, target, port, server_mode=False):
        self.target = target
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = None
        self.addr = None
        self.server_mode = server_mode

    def connect(self):
        if not self.server_mode:
            try:
                self.connect_server()
                return
            except Exception:
                raise Exception("Failed connected to server")
        else:
            self.start_server()
            return

    # 整合服务端和客户端的启动到一个方法，通过self.MODE来控制选择什么方法
    # 启动服务端
    def start_server(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.target, self.port))
        self.socket.listen(1)
        # TODO nonblocking这个模块的功能需要学习一下 目前还是阻塞模式，希望能够实现非阻塞
        self.conn, self.addr = self.socket.accept()     # self.conn for server
        # TODO 给每个客户端创建一个独立的线程进行管理 不知道怎么实现来着，先用单线程试试

    # 客户端连接服务端
    def connect_server(self):       # TODO
        self.socket.connect((self.target, self.port))
        self.conn = self.socket     # self.conn for client

    # 用于self.conn的赋值和使用的封装，减少对self.conn的直接访问 因为self.conn在init里面没法初始化，所以这样干？
    def get_connection(self):       # TODO
        if not self.conn:
            raise ValueError("Connection is not established yet")
        return self.conn

    def disconnect(self):
        self.conn.close()
        self.socket.close()
        print("Disconnected over")
    # 可能会使用到select模块 epoll kqueue 等用来进行多路复用的模块

    def send(self, data):
        if isinstance(data, bytes):
            self.socket.sendall(data)
        else:
            self.socket.sendall(data.encode())

    def receive(self, buffer_size=BUFFER_SIZE):
        return self.socket.recv(buffer_size)

    # 擅自给两个receive加上了decode为'utf-8' 默认是这个吧？？
    def receive_once(self):
        receive_data = b''      # 注意receive_data是个b''
        if self.conn:
            while True:
                chunk = self.conn.recv(self.BUFFER_SIZE)
                receive_data += chunk
                if len(chunk) < self.BUFFER_SIZE:
                    break       # 接受完最后的数据以后就break
            return receive_data.decode('gbk')
        else:
            raise Exception("No connection")

    # 封装异常处理的函数
    def handle_exception(self, e):
        print(self.ERROR_MESSAGE)

    # 用于设置非阻塞，使用fcntl模块     # TODO 如果只是单个连接 好像没有必要
    def set_nonblocking(self, sock):
        pass

    # 用于上下文管理 socket (不过好像不需要定义一个方法，而是在main中调用实例的时候用with netcat这种使用)上下文管理是为了防止资源泄露
    def with_socket(self):
        pass

    def flush_socket_buffer(self):
        # TODO self.conn or self,socket
        # 刷新接受缓存区
        self.conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 0)
        # 刷新发送缓存区
        self.conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0)
        # self.socket.fileno()
        # while self.socket.recv(self.BUFFER_SIZE):
        #     pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        self.socket.close()


class Command:
    # 其实这里可以使用一个nettool的高级类，给command类传一个nettool类，能用ssh/telnet/之类的协议来，但是现在只为了实现一个netcat就没做
    #  所以传入的就是一个netcat实例
    def __init__(self, netcat):
        self.netcat = netcat
        self.cmd = None

    def parse_command(self, cmd):
        self.cmd = shlex.split(cmd)
        cmd_type = self.cmd[0]
        if cmd_type == 'exit':
            self.netcat.disconnect()
            return
        elif cmd_type == 'cd':
            os.chdir(self.cmd[1:])  # TODO 有点不全面，只能执行一条命令，待检查测试
            output = 'Reminder: cd finished'
        elif cmd_type == 'pwd':
            output = os.getcwd()
            print(output)
        else:
            output = self.execute_command()
        self.send_command_back(output)
        return

    # 执行命令这块里面，据说不建议使用os.popen，因为错误输出等不完善已经过时，应使用subprocess里面的比较好
    def execute_command(self):
        try:
            # 该设置 stderr=subprocess.STDOUT 参数将标准错误输出合并到标准输出中，以便将它们作为一个字符串返回。否则，如果命令执行失败，
            # check_output() 函数只会返回标准输出，并引发一个 CalledProcessError 异常。
            output = subprocess.check_output(self.cmd, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            # print(output.decode())
            # self.netcat.get_connection().send(output)
            return output
        except Exception as e:
            self.netcat.handle_exception(e)     # 这里需要返回值吗

    def send_command_back(self, output):
        self.netcat.get_connection().send(output)


class FileInfo:
    def __init__(self, path, size):
        self.path = path
        self.size = size


class FileTransmitter:
    BLOCK_SIZE = 4096

    def __init__(self, netcat):         # 承载一个代码实例
        self.netcat = netcat

    def send_file(self, filename):
        self.netcat.flush_socket_buffer()
        try:
            if os.path.isfile(filename):
                # filesize = os.path.getsize(filename)
                # netcat.get_connection().send(f"{filename} {filesize}".encode()) # 这个提示不太确定要不要加，
                # 因为不知道如何区分传输的是提示语还是文件的字节的一部分
                with open(filename, 'rb') as f:
                    while True:
                        data = f.read(netcat.BUFFER_SIZE)
                        if not data:
                            print("transfer over")
                            break
                        netcat.send(data)
                    print("up open file end..")
        except Exception as e:
            self.netcat.handle_exception(e)
        finally:
            return

    def receive_file(self, filename):
        tmp_path = "D:\\Py0401\\try1st\\A-Tool-HomeWork\\tmp"
        save_path = os.path.join(tmp_path, 'received')
        # 因为担心缓冲区没有刷新干净，担心提示语和文件的字节混淆，所以不知道咋办
        self.netcat.flush_socket_buffer()
        try:
            with open(save_path, "wb") as f:
                # 修改了get_connection，现在在进行测试
                while True:
                    data = netcat.receive_once().encode()
                    f.write(data)
                    if not data:
                        print("recv over")
                        break
                print("down success..")
        except Exception as e:
            self.netcat.handle_exception(e)


class Security:
    def __init__(self, netcat):
        self.netcat = netcat

    def authenticate(self):
        pass

    def encrypt(self, data):
        pass

    def decrypt(self, data):
        pass


if __name__ == '__main__':
    # target = input("input ip:")
    # port = input("port")
    target = '127.0.0.1'
    port = 5555
    mode = input('serve_mode:(t/f)')
    # cmd = 'whoami'
    if mode == 't':
        server_mode = True
    else:
        server_mode = False
    netcat = NetCat(target, port, server_mode)
    # with netcat:
    netcat.connect()
    # below it is recv and send test
    # if mode == 'f':
    #     # "I send you message could you recv?"
    #     while True:
    #         try:
    #             send_msg = input("input your msg: (exit to quit)")
    #             netcat.get_connection().send(send_msg.encode())
    #             if send_msg == 'exit':
    #                 break
    #             recv_msg = netcat.receive_once()
    #             print(recv_msg)
    #             if recv_msg == 'exit':
    #                 break
    #         except KeyboardInterrupt:
    #             netcat.disconnect()
    #             break
    # else:
    #     while True:
    #         try:
    #             recv_msg = netcat.receive_once()
    #             print(recv_msg)
    #             if recv_msg == 'exit':
    #                 break
    #             send_msg = input("input your msg: (exit to quit)")
    #             netcat.get_connection().send(send_msg.encode())
    #             if send_msg == 'exit':
    #                 break
    #         except KeyboardInterrupt:
    #             netcat.disconnect()
    #             break
    # below it is command test

    # below it is cmd test
    # if mode == 't':
    #     while True:
    #         cmd = netcat.receive_once()
    #         # if cmd == 'exit':
    #         #     netcat.disconnect()
    #         #     break
    #         command = Command(netcat)
    #         command.parse_command(cmd)
    # else:
    #     while True:
    #         cmd = input("input your cmd")
    #         if cmd == 'exit':
    #             netcat.get_connection().send(cmd.encode())
    #             netcat.disconnect()
    #         netcat.get_connection().send(cmd.encode())
    #         result = netcat.receive_once()
    #         print(result)

    # 还是在self.socket 和self.conn遇到了问题，使用的send和receive都是netcat的，要注意区分两个的区别，尤其是服务端server
    if mode != 't':
        while True:
            filename = input("input filename you want to up")
            netcat.send(filename)
            if filename == 'exit':
                netcat.disconnect()
                break
            response = netcat.receive()
            try:
                if response.decode() == 'ok':
                    print("确认文件名，开始传输文件...")
                    filetrans = FileTransmitter(netcat)
                    filetrans.send_file(filename)
                    recv_msg = netcat.receive()
                    print(recv_msg)
                else:
                    print("对方拒绝文件")
            except Exception as e:
                netcat.handle_exception(e)
    else:
        while True:
            filename = netcat.receive_once()
            if filename == 'exit':
                netcat.disconnect()
                break
            print(f"receive {filename}")
            confirm_msg = 'ok'
            netcat.get_connection().send(confirm_msg.encode())
            print("receiving ing...")
            try:
                filetrans = FileTransmitter(netcat)
                filetrans.receive_file(filename)
                netcat.send("server received")
            except Exception as e:
                netcat.handle_exception(e)



