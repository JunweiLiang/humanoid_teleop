import socket
import datetime

HOST = '0.0.0.0'  # Listen on all available interfaces
PORT = 12345

def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                # Send current UTC timestamp
                current_time_utc = datetime.datetime.utcnow().timestamp()
                conn.sendall(str(current_time_utc).encode())

if __name__ == "__main__":
    run_server()
