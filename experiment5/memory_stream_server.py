#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

class DynamicMemoryStreamer(BaseHTTPRequestHandler):
    # FIX: Route HEAD requests directly through your GET logic to satisfy curl -I
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        # Handle the script's sanity check health probe cleanly
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            # Only write a body if it's not a HEAD request
            if self.command != 'HEAD':
                self.wfile.write(b"OK")
            return

        # Handle the actual memory dirtying chunk streaming
        if self.path.startswith('/chunk/'):
            try:
                mb_size = int(self.path.split('/')[-1])
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                
                # Only stream out data chunks for actual GET requests
                if self.command != 'HEAD':
                    chunk_buffer = b"X" * (1024 * 1024)
                    for _ in range(mb_size):
                        self.wfile.write(chunk_buffer)
                return
            except Exception as e:
                return
                
        self.send_response(404)
        self.end_headers()

def run(port=9000):
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, DynamicMemoryStreamer)
    print(f"Host payload generator streaming active at port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down streaming engine.")
        sys.exit(0)

if __name__ == '__main__':
    run()
