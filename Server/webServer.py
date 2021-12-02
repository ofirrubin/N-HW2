import concurrent.futures
import json
import mimetypes
import re
import socket
import os
import threading
import time


MIN = 60
HOUR = 60 * MIN
DAY = 24 * HOUR
CLOSE_AFTER = 0  # Soft Close - Seconds (float) - Set 0 to no limit


# HTTP 1.1 Server
class WebServer:

    def __init__(self, config):
        self.ip = config["ip"]
        self.port = config["port"]
        self.devices = config["backlog"]
        self.wroot = config["webroot"]
        self.errors = config["errors"]
        self.redirects = config["redirected"]
        self.packet_size = config["packet_size"]

        # You must include a valid webroot.
        if os.path.isdir(self.wroot) is False:
            raise ValueError("You must set an existing web root to contain the webserver data")
        self.s = socket.socket()
        self.up = False

    def start(self):
        # Setting up the server and making it ready for a connection
        try:
            self.s.bind((self.ip, self.port))
            self.s.listen(self.devices)
            self.up = True
        except (socket.error, OSError) as e:
            print("Error: ", e)
            exit(0)
        # This allows us a multiple calls at the time, ThreadPool is like Thread object but limiting number of threads.
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.devices) as executor:
            # As long as we are allowed to get requests
            while self.up:
                try:
                    executor.submit(self.__client_handler, self.s.accept())  # Accept clients at background.
                except Exception as e:
                    print("An error occured: ", e)
            print("Server is closing...")
        self.s.close()  # Close server
        print("Server closed.")

    def stop(self):
        print("Stop command sent...")
        self.up = False  # From now on, the server is not allowed to take more clients, and the socket is closed.
        try:  # Dummy connect to prevent being stuck by accept
            s = socket.socket()
            s.connect((self.ip, self.port))  # Connect to the server as set
            s.close()
        except socket.error:  # We don't care about any exception thrown, it's just a dummy.
            pass

    def get_response(self, req):
        # The function gets a get request and returns the value to send (bytes).
        resp = []
        req = req.strip('\\')
        if req in self.redirects.keys():
            resp.append(("HTTP/1.1 301 Moved Permanently\r\nLocation: \\" + self.redirects[req]).encode())
        else:
            if os.path.isfile(os.path.join(self.wroot, req)):
                resp.append("HTTP/1.1 200 OK\r\n".encode())
            else:
                resp.append("HTTP/1.1 404 Not Found\r\n".encode())
                req = self.errors["404"]

            resp.append(("Content-Type: " + mimetypes.guess_type(req)[0] + "\r\n\r\n").encode())  # END OF HEADER
            try:
                with open(os.path.join(self.wroot, req), 'rb') as f:
                    resp.append(f.read())
            except (FileNotFoundError, OSError):  # Default error page
                resp.append(
                    """<!doctype html>\n<html lang="en">\n<head>\n   <meta charset="utf-8">\n   <title>Server could not load
             the file.</title>\n   <meta name="description" content="Server Error">\n    <meta name="Server Page" content=
             "Page Not Found">\n</head>\n<body>Server Error\n</body>\n</html>""".encode())

        return b''.join(resp)

    def __client_handler(self, client):
        c, c_addr = client
        if self.up is False:
            return
        print("accepting client at", c_addr)

        # Easy send and receive functions, send func created just for a closer syntax to the recv func.
        def recv(cl, packet_size):
            data = cl.recv(packet_size)
            r = data
            while len(r) == packet_size:
                r = cl.recv(packet_size)
                data += r
            return r

        def send(cl, data):
            cl.sendall(data)
        try:
            d = recv(c, self.packet_size).decode()
            try:
                # Handling HTTP 1.1 Calls:
                # Alias index call check:
                if d.split("\r\n", maxsplit=2)[0] == "GET / HTTP/1.1":
                    match = "index.html"
                else:
                    # Any other GET Call check
                    match = re.match("GET /(.+) HTTP/1.1", d)
                    if match is not None:
                        match = match[1]

                # We responding to calls we know how to answer
                if match is not None:
                    send(c, self.get_response(match))
            except re.error:
                match = d  # perhaps for later case if I want to improve the server... - just so I won't forget

        except UnicodeDecodeError as e:
            print("Error decoding client message")

        # Closing the connection with the client at the end.s
        try:
            c.close()
        except socket.error:
            pass


def timed_close(ws, t):  # The function closes the server after t seconds, set t to 0 for unlimited time.
    if t == 0:
        return
    time.sleep(t)
    ws.stop()


with open("config.json", "r") as f:
    w = WebServer(json.loads(f.read()))
    threading.Thread(target=timed_close, args=(w, CLOSE_AFTER)).start()
    w.start()
