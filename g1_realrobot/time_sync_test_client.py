import socket
import time
import argparse
import datetime

parser = argparse.ArgumentParser()
parser.add_argument("server_ip")
parser.add_argument("--port", type=int, default=12345)

NUM_PINGS = 10

def get_time_difference(server_ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        start_time_client = time.time()
        s.connect((server_ip, port))
        end_time_client = time.time()

        # Measure network latency for this specific communication
        latency = (end_time_client - start_time_client) * 1000 # in milliseconds

        # Send a dummy request to get the server's time
        s.sendall(b"get_time")
        server_time_str = s.recv(1024).decode()
        server_time_utc = float(server_time_str)

        # Estimate the server's time upon arrival at the client
        # We assume half of the measured latency is for one-way travel
        estimated_server_time_at_client = server_time_utc + (latency / 2000) # divide by 1000 for ms to seconds, then by 2 for one way

        # Get current client time (UTC)
        current_client_time_utc = datetime.datetime.utcnow().timestamp()

        # Calculate the difference
        time_difference = (current_client_time_utc - estimated_server_time_at_client) * 1000 # in milliseconds

        print(f"Network Latency (RTT): {latency:.2f} ms. (Time spend connected to the server)")
        print(f"Server UTC Timestamp: {datetime.datetime.fromtimestamp(server_time_utc, datetime.timezone.utc)}")
        print(f"Client UTC Timestamp: {datetime.datetime.fromtimestamp(current_client_time_utc, datetime.timezone.utc)}")
        print(f"Estimated Time Difference (Client - Server): {time_difference:.2f} ms")
        print("A positive value means the client's clock is ahead of the server's clock.")
        print("A negative value means the client's clock is behind the server's clock.")


if __name__ == "__main__":
    args = parser.parse_args()
    get_time_difference(args.server_ip, args.port)
