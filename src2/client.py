import os
import sys
import socket
import threading

# Local Imports
from packet_type import PacketType
from packet import HEADER_SIZE, encode_header, decode_header, recv_generator


class Client:
    def __init__(self, username: str, hostname: str, port: int):
        self.username = username
        self.server_hostname = hostname
        self.server_port = port

        self.is_connected = False
        self.save_directory = f'{username}/'
        self.new_username_requested = False

    def start(self):
        # Setup socket
        print(f"Connecting to {self.server_hostname}:{self.server_port}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.server_hostname, self.server_port))
        except ConnectionRefusedError:
            print("Could not connect to server")
            sys.exit()
        self.is_connected = True

        print(f"Connected to {self.server_hostname}:{self.server_port}")

        # Start a new thread to handle communication with the server
        server_thread = threading.Thread(target=self.handle_server_response)
        server_thread.daemon = True
        server_thread.start()

        self.send_username()
        self.handle_cli_input()

    def send_username(self):
        header = encode_header(PacketType.USERNAME, 0, username=self.username)
        self.socket.sendall(header)
        self.new_username_requested = False
    
    def handle_server_response(self):
        while self.is_connected:
            try:
                data = self.socket.recv(HEADER_SIZE)
            except ConnectionResetError:
                print('Disconnected from the server')
                self.close()
                break

            if not data:
                continue

            expected_type, expected_size, params = decode_header(data)

            if expected_type == PacketType.DOWNLOAD:
                datastream = recv_generator(self.socket, expected_size)
                filename = params.get('filename')
                self.process_download(datastream, filename)
                continue

            message = self.socket.recv(expected_size).decode()

            match expected_type:
                case PacketType.ANNOUNCEMENT:
                    self.process_announcement(message)
                case PacketType.DUPLICATE_USERNAME:
                    self.process_duplicate_username(message)
                case PacketType.FILE_LIST:
                    print(f'Available files:\n{message}')
                case PacketType.IN_MESSAGE:
                    sender = params.get('sender')
                    self.process_in_message(message, sender)

    def process_in_message(self, message, sender):
        if sender:
            print(f'{sender}: {message}')
        else:
            print(f'{message}')

    def process_announcement(self, message):
        print(f'{message}')

    def process_duplicate_username(self, user_list):
        print(f'This username is already taken\n'
              f'Current users connected to the server: {user_list}\n'
              f'Enter a new username: ', end='')
        self.new_username_requested = True

    def process_download(self, datastream, filename):
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)

        download_path = self.save_directory + filename
        print(f"File will be saved to: {download_path}")

        with open(download_path, 'wb') as file:
            for file_data in datastream:
                file.write(file_data)

        print(f"File saved to: {download_path}")

    def handle_cli_input(self):
        while True:
            try:
                user_input = str(input()).rstrip()
            except KeyboardInterrupt as e:
                print('Detected Keyboard Interrupt')
                self.close()
                break

            if not self.is_connected:
                break
            if not user_input:
                continue
            if self.new_username_requested:
                self.username = user_input
                self.send_username()
                continue

            match user_input.split(maxsplit=2):
                case ['/disconnect']:
                    print('Disconnecting from server')
                    self.close()
                case ['/msg', username, user_input]:
                    # Direct message a specific client
                    if username == self.username:
                        print(f'Select someone other than yourself to directly message')
                        return
                
                    message = user_input.encode()
                    header = encode_header(PacketType.OUT_MESSAGE, len(message), recipient=username)
                    self.socket.sendall(header + message)
                case ['/list_files']:
                    # Request a list of all available files
                    header = encode_header(PacketType.FILE_LIST_REQUEST, 0)
                    self.socket.sendall(header)
                case ['/download', filename]:
                    # Request to download a certain file
                    header = encode_header(PacketType.DOWNLOAD_REQUEST, 0, filename=filename)
                    self.socket.sendall(header)
                case _:
                    # Send message to everyone
                    message = user_input.encode()
                    header = encode_header(PacketType.OUT_MESSAGE, len(message))
                    self.socket.sendall(header + message)

    def close(self):
        self.is_connected = False
        if self.socket.fileno() != -1:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        sys.exit()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python client.py [username] [hostname] [port]")
        sys.exit(1)

    username = sys.argv[1]
    hostname = sys.argv[2]

    try:
        port = int(sys.argv[3])
    except ValueError:
        print("Invalid port number. Port must be an integer.")
        sys.exit(1)

    client = Client(username, hostname, port)
    client.start()
