import os
import re
import socket
from urllib3 import util
import sys

VERSION = "1.1"


# NOTE THAT THIS IS HTTP 1.1 WEB CLIENT, I didn't want to use the request lib.
class WebClient:
    def __init__(self, ip, port, timeout=None):
        self.ip = ip
        self.port = port
        self.timeout = timeout

    def request_get(self, request, packet_size=1024):
        # Name is in reverse so that others won't think it's returning a request,
        # The function returns the response of GET request
        def recv(sock):
            rv = sock.recv(packet_size)
            d = [rv]
            while rv is not None and len(rv) == packet_size:
                rv = sock.recv(packet_size)
                d.append(rv)
            return b''.join(d)

        try:
            s = socket.socket()
            if self.timeout is not None:
                s.settimeout(self.timeout)
            s.connect((self.ip, self.port))
            r = "GET /" + request + " HTTP/" + VERSION
            s.sendall(r.encode())
            data = recv(s)
            if b"\r\n" in data:
                m = data.replace(b"Location: ", b"").split(b"\r\n", maxsplit=1)
                if re.match("HTTP/" + VERSION + " 301 Moved Permanently", m[0].decode()) is not None:
                    print("Redirected, requesting new file: ", m[1].decode())
                    return self.request_get(m[1].decode(), packet_size)
            return data
        except (socket.error, OSError) as e:  # Socket and timeout exceptions
            print("\n\nAn error occured: ", e)

    @staticmethod
    def status(response: bytes):
        return None if response is None else response.split(b'\r\n')[0]  # First part of the message

    @staticmethod
    def content(response: bytes):
        if response is None:
            return
        d = response.split(b'\r\n\r\n', maxsplit=1)  # The header ends with 2x "\r\n"
        if d is None or len(d) < 2:
            return None
        return d[1]

    def requirements(self, html: str, include_prefix=True):
        req = re.findall("src=\"(.+)\"", html)
        if include_prefix:
            this = []
            other = []
            for x in req:
                x = x.split('"', maxsplit=1)[0]
                if self.ip in x or len(list([y for y in x.split("/", maxsplit=1) if y != ''])) == 1:
                    this.append(x)
                else:
                    other.append(x)
            return {"this": this, "other": other}

        else:
            return req


def show_page(client, page):
    response = cl.request_get(page)
    if response is not None:
        print("Status: ", client.status(response).decode())
        print("Content: ", client.content(response))
        req = client.requirements(response.decode())
        print("The page requires the following resources too:\nFrom this host: ", req["this"], "\nFrom other hosts: ",
              req["other"])


def save_content(resource_name, client, response, save_at):
    status = client.status(response)
    if status == b"HTTP/1.1 404 Not Found":
        print("=> NOTE: the requested resource ", resource_name, "is PageNotFound page")
    elif status != b'HTTP/1.1 200 OK':
        return False

    try:
        p = os.path.join(save_at, resource_name)
        if os.path.exists(os.path.dirname(p)) is False:
            os.makedirs(os.path.dirname(p))
        with open(p, "wb") as f:
            f.write(client.content(response))
    except OSError as e:
        print("Error occured: ", e)
        return False
    return True


def download_all(client, page, d):
    # Save page for offline view, save external resources too as aliases.
    # Get the required page and save it's content
    response = client.request_get(page)
    content = client.content(response)
    if response is None or content is None:
        return

    # This function will set aliases for external resources with local files names.
    def replace_src(src_name, new_name):
        content.replace("src=\"" + src_name + "\"", "src=\"" + new_name + "\"")

    # If the resource is empty, this is an alias for index.html
    if b'src="\\"' in content:
        content.replace(b'src="\\"', b'src="index.html"')
    req = client.requirements(content.decode())  # Get all page requirements

    for this_req in req["this"]:
        resp = client.request_get(this_req)
        save_content(this_req, client, resp, d)

    # The following part will get stuck if any because of connection issue.
    file_n = 0  # External aliases
    for other_req in req["other"]:
        u = other_req.replace("https", "http", 1)  # Try getting it using HTTP and not https
        addr = util.parse_url(u)
        v = u.replace(addr.host, "").replace(addr.scheme + "://", "")
        if v.startswith("/"):
            v = v[1:]
        # Here we will also use timeout if the connection is stuck, we should try others too.
        other_client = WebClient(addr.host, 80, 5)
        file_name, file_ext = os.path.splitext(u)
        resp = other_client.request_get(v)
        filename = str(file_n) + file_ext
        if save_content(filename, other_client, resp, d):
            file_n += 1
            replace_src(other_req, os.path.join(d, filename))
            print(other_req, " Saved as " + filename)
        else:
            print("Couldn't save: ", other_req, " might require POST request which is not supported by the client.")

    if page == "":
        page = "index.html"
    save_content(page, client, response, d)  # Save the file after the internals have changed


if __name__ == "__main__":

    args = sys.argv[1:]
    if 3 > len(args) or len(args) > 4:
        print("""Allowed syntax:
         <HOST> <PORT> <FILENAME>
         Examples, in my server you can try:
         => 127.0.0.1 1024 image.png
         => 127.0.0.1 80 index.html
         You may also want to save the page or files, thus use the following syntax:
         <HOST> <PORT> <FILENAME> <OUTPUT-DIR>""")
        exit(0)
    # print("HTTP Web Client\nWelcome!\nWe are just getting started..")
    cl = WebClient(args[0], int(args[1]))
    try:
        if len(args) == 3:  # Show page
            print("Did you know that the program also allows you to save the page?\n"
                  "Give it a try with this syntax: <HOST> <PORT> <FILENAME> <OUTPUT-DIR>\n\n")
            show_page(cl, args[2])
        else:  # Download all
            print("Did you know that you could see the page details and requirements without saving?\n"
                  "Give it a try with this syntax: <HOST> <PORT> <FILENAME>\n\n")
            download_all(cl, args[2], args[3])
    except (OSError, socket.error, UnicodeDecodeError) as e:
        print("An error occured: ", e)
    print("\nAll done!")

