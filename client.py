import sys
import socket

class Client:
    def __init__(self, username, hostname, port):
        self.username = username
        self.serverHostname = hostname
        self.serverPort = port

    def connect(self):
        print(f"Connecting to server with username '{self.username}', hostname '{self.serverHostname}', and port self{self.serverPort}")

        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((self.serverHostname, self.serverPort))

        while True:

            message = input("Input lowercase sentence: ")
            match message:
                case '/disconnect':
                    clientSocket.close()
                    break

            clientSocket.send(message.encode())
            modifiedMessage = clientSocket.recv(1024).decode()
            print(f'Server: {modifiedMessage}')
            


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
    client.connect()
