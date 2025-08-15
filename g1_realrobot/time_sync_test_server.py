import socket
import time

HOST = '0.0.0.0'
PORT = 12346

def run_latency_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Latency Server listening on {HOST}:{PORT}")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                # Echo back the received data
                conn.sendall(data)

if __name__ == "__main__":
    run_latency_server()
