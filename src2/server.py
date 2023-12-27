# Standard Library Imports
import sys
import socket
import threading
import select

# Local Imports
from packet_type import PacketType
from packet import (
    HEADER_SIZE,
    encode_header,
    decode_header
)
from log_event import LogEvent
from logger import Logger


class ClientConnection:
    def __init__(self, socket: socket.socket, address: tuple[str, int]):
        self.socket = socket
        self.address = address
        self.username = None


class Server:
    def __init__(self, port: int):
        # Init key variables and create logger
        self.port = port
        self.is_running = False
        self.logger = Logger('./server.log')
        self.files_path = 'download'
        self.connections: list[ClientConnection] = []

    def start(self):
        # Start a new thread to handle communication with the server
        server_thread = threading.Thread(target=self.run_server)
        server_thread.daemon = True
        server_thread.start()

        self.handle_cli_input()

    def handle_cli_input(self):
        while True:
            try:
                input()
            except:
                print('Detected Keyboard Interrupt')
                sys.exit(0) 

    def run_server(self):
        # Begin starting the server
        self.logger.log(LogEvent.SERVER_INIT_START, port=self.port)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.socket.bind(("", self.port))
        self.socket.listen(1)
        self.is_running = True

        self.logger.log(LogEvent.SERVER_STARTED, port=self.port)

        self.listen()

    def listen(self):
        self.logger.log(LogEvent.SERVER_LISTENING, port=self.port)

        while self.is_running:
            readables = [self.socket] + [c.socket for c in self.connections]

            readable, _, _ = select.select(readables, [], [])

            for sock in readable:
                if sock is self.socket:
                    client_socket, addr = self.socket.accept()
                    self.logger.log(LogEvent.USER_CONNECT, ip_address=addr[0], client_port=addr[1])

                    conn = ClientConnection(client_socket, addr)
                    self.connections.append(conn)
                else:
                    self.process_socket(sock)

    def process_socket(self, socket: socket.socket):
        conn = self.get_conn_by_socket(socket)

        data = socket.recv(HEADER_SIZE)
        if not data:
            return

        expected_type, expected_size, params = decode_header(data)

        message = socket.recv(expected_size).decode()

        match expected_type:
            case PacketType.METADATA:
                username = params.get('username')
                self.process_metadata_packet(conn, username)

            case PacketType.OUT_MESSAGE:
                recipient = params.get('recipient')
                self.process_message_packet(conn, recipient, message)

            case PacketType.FILE_LIST_REQUEST:
                self.process_file_list_request(conn)

            case PacketType.DOWNLOAD_REQUEST:
                filename = params.get('filename')
                self.process_download_request(conn, filename)

    def process_metadata_packet(self, conn: ClientConnection, username: str):
        if username in [conn.username for conn in self.connections]:
            self.handle_duplicate_username(conn)
            return
        conn.username = username

        self.logger.log(LogEvent.PACKET_RECEIVED, username=username, content=username)

        message = f'{username} has joined the chat.'.encode()
        header = encode_header(PacketType.ANNOUNCEMENT, len(message))
        self.broadcast(header + message, exclude=[username])

    def handle_duplicate_username(self, conn):
        pass

    def process_message_packet(self, conn: ClientConnection, recipient: [None|str], message: str):
        pass

    def process_file_list_request(self, conn: ClientConnection):
        pass

    def process_download_request(self, conn: ClientConnection, filename: str):
        filepath = f'{self.files_path}/{filename}'

        try:
            with open(filepath, 'rb') as file:
                file_bytes = file.read()
        except FileNotFoundError:
            print(f"File not found: {filepath}")
            return
        
        header = encode_header(PacketType.DOWNLOAD, len(file_bytes), filename=filename)

        self.unicast(header + file_bytes, conn.username)

        self.logger.log(LogEvent.DOWNLOAD_REQUEST, username=conn.username, filename=filename)

    def broadcast(self, data: bytes, exclude: list[str]=[]):
        for conn in self.connections:
            if conn.username in exclude:
                continue

            conn.socket.sendall(data)

            self.logger.log(LogEvent.PACKET_SENT, username=conn.username)

    def unicast(self, data: bytes, recipient: str):
        for conn in self.connections:
            if conn.username == recipient:
                conn.socket.sendall(data)
                print(data)

                self.logger.log(LogEvent.PACKET_SENT, username=recipient)
                return

    def get_conn_by_socket(self, socket):
        for conn in self.connections:
            if conn.socket == socket:
                return conn
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python server.py [port]")
        sys.exit(1)

    # Convert port input parameter to integer
    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Invalid port number. Port must be an integer.")
        sys.exit(1)

    # Create and start server
    server = Server(port)
    server.start()
