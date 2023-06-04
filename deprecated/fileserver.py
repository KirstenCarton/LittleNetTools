import socket

target = '127.0.0.1'
port = 5555

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((target, port))
    sock.listen()
    conn, addr = sock.accept()
    print(f"{addr} connected success")
    with open('download.txt', 'wb') as f:
        while True:
            data = conn.recv(1024)
            f.write(data)
            if not data:
                print("recv over")
                break


