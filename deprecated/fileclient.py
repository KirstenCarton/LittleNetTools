import socket


target = '127.0.0.1'
port = 5555

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((target, port))
    print(f"connected success")
    filename = input("filename:")
    with open(filename, 'rb') as f:
        while True:
            data = f.read(1024)
            if not data:
                print(f"transfer over")
                break
            sock.send(data)
