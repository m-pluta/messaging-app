# Setup
import sys

# Logging
from logger import Logger, LogEvent

# Packets
from packet import Packet, MessagePacket

# Main
import socket
import uuid
import threading


class ClientConnection:
    nextID = 0

    def __init__(self, socket, address):
        self.socket = socket
        self.ip_address = address[0]
        self.port = address[1]
        self.uuid = ClientConnection.nextID
        ClientConnection.nextID += 1

    # TODO: replace ids with uuid
    def generateUUID(self):
        return str(uuid.uuid4())


class Server:
    def __init__(self, port):
        # Init key variables and create logger
        self.port = port
        self.logger = Logger('./server.log')
        self.currentConnections = {}

    def start(self):
        # Begin starting the server
        self.logger.log(LogEvent.SERVER_INIT_START, port=self.port)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("", self.port))
        self.socket.listen(1)
        self.is_running = True
        self.logger.log(LogEvent.SERVER_STARTED, port=self.port)

        self.listen()

    def listen(self):
        self.logger.log(LogEvent.SERVER_LISTENING, port=self.port)

        while self.is_running:
            # New client tried to establish a connection
            cSocket, addr = self.socket.accept()
            conn = ClientConnection(cSocket, addr)
            self.currentConnections[conn.uuid] = conn
            self.logger.log(LogEvent.USER_CONNECT, uuid=conn.uuid,
                            ip_address=conn.ip_address, clientPort=conn.port)

            # Start a new thread to handle communication with the new client
            cThread = threading.Thread(target=self.handleClient, args=(conn,))
            cThread.start()
            self.logger.log(LogEvent.USER_THREAD_STARTED, uuid=conn.uuid)

        self.closeServer()

    def handleClient(self, conn):
        while True:
            # Check if client disconnected
            data = conn.socket.recv(1024)
            if not data:
                break

            incoming_packet = Packet.loads(data.decode())
            match (incoming_packet['type']):
                case 'metadata':
                    self.logger.log(LogEvent.PACKET_RECEIVED,
                                    uuid=conn.uuid,
                                    content=incoming_packet['username'])
                    conn.username = incoming_packet['username']
                case 'message':
                    self.logger.log(LogEvent.PACKET_RECEIVED,
                                    uuid=conn.uuid,
                                    content=incoming_packet['content'])
                    modifiedMessage = incoming_packet['content'].upper()

                    # Resend modified message
                    outgoing_packet = MessagePacket(conn.username,
                                                    content=modifiedMessage)
                    conn.socket.send(outgoing_packet.to_json().encode())
                    self.logger.log(LogEvent.PACKET_SENT,
                                    uuid=conn.uuid,
                                    content=modifiedMessage)
                case 'file_list_request':
                    pass
                case 'file_request':
                    pass

        self.closeClient(conn.uuid)

    def closeClient(self, uuid):
        self.logger.log(LogEvent.USER_DISCONNECT, uuid=uuid)
        self.currentConnections[uuid].socket.close()
        del self.currentConnections[uuid]

    def closeServer(self):
        self.is_running = False
        self.socket.close()
        self.logger.log(LogEvent.SERVER_CLOSE)


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
