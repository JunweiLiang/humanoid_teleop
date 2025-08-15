import socket
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("server_ip")
parser.add_argument("--port", default="12346")

NUM_PINGS = 10

def measure_latency(server_ip, port):
    latencies = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((server_ip, port))
            print(f"Connected to {server_ip}:{port}")
            for i in range(NUM_PINGS):
                start_time = time.time()
                s.sendall(b"ping") # Send a small packet
                data = s.recv(1024) # Wait for response
                end_time = time.time()

                rtt = (end_time - start_time) * 1000 # Convert to milliseconds
                latencies.append(rtt)
                print(f"Ping {i+1}: {rtt:.2f} ms")
                time.sleep(0.1) # Wait a bit before next ping

            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                print(f"\n--- Latency Statistics ({server_ip}) ---")
                print(f"Pings sent: {NUM_PINGS}")
                print(f"Minimum RTT: {min_latency:.2f} ms")
                print(f"Maximum RTT: {max_latency:.2f} ms")
                print(f"Average RTT: {avg_latency:.2f} ms")

        except ConnectionRefusedError:
            print(f"Connection refused. Make sure the server is running on {server_ip}:{port}")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    args = parser.parse_args()
    measure_latency(args.server_ip, args.port)
