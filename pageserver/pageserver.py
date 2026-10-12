"""
  A trivial web server in Python.

  Based largely on https://docs.python.org/3.4/howto/sockets.html
  This trivial implementation is not robust:  We have omitted decent
  error handling and many other things to keep the illustration as simple
  as possible.

  FIXME:
  Currently this program always serves an ascii graphic of a cat.
  Change it to serve files if they end with .html or .css, and are
  located in ./pages  (where '.' is the directory from which this
  program is run).
"""

import config    # Configure from .ini files and command line
import logging   # Better than print statements
logging.basicConfig(format='%(levelname)s:%(message)s',
                    level=logging.INFO)
log = logging.getLogger(__name__)
# Logging level may be overridden by configuration 

import socket    # Basic TCP/IP communication on the internet
import _thread   # Response computation runs concurrently with main program
import os
from urllib.parse import urlsplit, unquote


def listen(portnum):
    """
    Create and listen to a server socket.
    Args:
       portnum: Integer in range 1024-65535; temporary use ports
           should be in range 49152-65535.
    Returns:
       A server socket, unless connection fails (e.g., because
       the port is already in use).
    """
    # Internet, streaming socket
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind to port and make accessible from anywhere that has our IP address
    serversocket.bind(('', portnum))
    serversocket.listen(1)    # A real server would have multiple listeners
    return serversocket


def serve(sock, func):
    """
    Respond to connections on sock.
    Args:
       sock:  A server socket, already listening on some port.
       func:  a function that takes a client socket and does something with it
    Returns: nothing
    Effects:
        For each connection, func is called on a client socket connected
        to the connected client, running concurrently in its own thread.
    """
    while True:
        log.info("Attempting to accept a connection on {}".format(sock))
        (clientsocket, address) = sock.accept()
        _thread.start_new_thread(func, (clientsocket,))


##
# Starter version only serves cat pictures. In fact, only a
# particular cat picture.  This one.
##
CAT = """
     ^ ^
   =(   )=
"""

# HTTP response codes, as the strings we will actually send.
# See:  https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
# or    http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
##
STATUS_OK = "HTTP/1.0 200 OK"
STATUS_FORBIDDEN = "HTTP/1.0 403 Forbidden"
STATUS_NOT_FOUND = "HTTP/1.0 404 Not Found"
STATUS_NOT_IMPLEMENTED = "HTTP/1.0 501 Not Implemented"

def send_response(sock, status, body, content_type="text/plain"):
    response = (
        status + "\r\n"
        + "Content-Type: " + content_type + "\r\n"
        + "Content-Length: " + str(len(body.encode("utf-8"))) + "\r\n"
        + "Connection: close\r\n"
        + "\r\n"
        + body
    )

    transmit(response, sock)

def respond(sock):
    """
    This server responds only to GET requests (not PUT, POST, or UPDATE).
    Any valid GET request is answered with an ascii graphic of a cat.
    """
    sent = 0
    request = sock.recv(1024)  # We accept only short requests
    request = request.decode("utf-8", errors="replace")
    
    log.info("--- Received request ----")
    log.info("Request was {}\n***\n".format(request))

    parts = request.split()
    if len(parts) < 2 or parts[0] != "GET":
        send_response(
            sock,
            STATUS_NOT_IMPLEMENTED,
            "Only GET requests are supported"
        )
        return

    url_path = urlsplit(parts[1]).path
    url_path = unquote(url_path)

    relative_path = url_path.lstrip("/")

    if(
        url_path.startswith("//")
        or relative_path.startswith(("~", ".."))
        or ".." in relative_path.split("/")
    ):
        send_response(
            sock,
            STATUS_FORBIDDEN,
            "403 Forbidden"
        )
        return

    if not relative_path.endswith((".html", ".css")):
            send_response(
                sock,
                STATUS_NOT_FOUND,
                "404 Not Found"
            )
            return

    options = get_options()
    docroot = os.path.realpath(options.DOCROOT)

    file_path = os.path.realpath(
        os.path.join(docroot, relative_path)
    )

    if os.path.commonpath([docroot, file_path]) != docroot:
            send_response(
                sock,
                STATUS_FORBIDDEN,
                "403 Forbidden"
            )
            return

    if not os.path.isfile(file_path):
            send_response(
                sock,
                STATUS_NOT_FOUND,
                "404 Not Found"
            )
            return

    with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

    if relative_path.endswith(".html"):
        content_type = "text/html; charset=utf-8"
    else:
        content_type = "text/css; charset=utf-8"

    send_response(
        sock,
        STATUS_OK,
        content,
        content_type
    )


    sock.shutdown(socket.SHUT_RDWR)
    sock.close()
    return


def transmit(msg, sock):
    """It might take several sends to get the whole message out"""
    sent = 0
    while sent < len(msg):
        buff = bytes(msg[sent:], encoding="utf-8")
        sent += sock.send(buff)

###
#
# Run from command line
#
###


def get_options():
    """
    Options from command line or configuration file.
    Returns namespace object with option value for port
    """
    # Defaults from configuration files;
    #   on conflict, the last value read has precedence
    options = config.configuration()
    # We want: PORT, DOCROOT, possibly LOGGING

    if options.PORT <= 1000:
        log.warning(("Port {} selected. " +
                         " Ports 0..1000 are reserved \n" +
                         "by the operating system").format(options.port))

    return options


def main():
    options = get_options()
    port = options.PORT
    if options.DEBUG:
        log.setLevel(logging.DEBUG)
    sock = listen(port)
    log.info("Listening on port {}".format(port))
    log.info("Socket is {}".format(sock))
    serve(sock, respond)


if __name__ == "__main__":
    main()
