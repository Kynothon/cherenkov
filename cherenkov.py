#! /usr/bin/env python3

import socketserver
import hashlib
import threading
import random
import binascii
import socket
import hmac
import ast
import sys
import io

###
# Signaling 
###
class StreamTCPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.metadata = {}
        client = f'{self.client_address}'
        print(f'Connected: {client}')
        try:
            self.handcheck()
            self.process_command()
        except Exception as e:
            print(e)
        finally:
            print(f'Closed {client}')

    def hmac(self):
        signature = hmac.new("secret".encode(), "body".encode(), digestmod=hashlib.sha512)
        return signature.hexdigest()

    def send(self, message):
        self.wfile.write(f'{message}\n'.encode('utf-8'))

    def receive(self):
        while True:
            line = self.rfile.readline()
            if not line :
                return None
            else:
                command = line.decode('utf-8').strip()
                if len(command) > 0:
                    return command

    def client(self, ip, port, message):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect((ip, port))
            sock.sendall(bytes(message, 'ascii'))

    def handcheck(self):
        print("Handcheck")
        print(f'Received: {self.receive()}')
        self.send(f"200 {self.hmac()}")
        print(f'Received: {self.receive()}')
        self.send(f"200 Accepted, go ahead with stream metadata\n")
        partial = self.receive()
        while not partial.startswith('.'):
            parsed = partial.split(':')
            if len(parsed) == 2:
                self.metadata[parsed[0]] = parsed[1].strip()
            partial = self.receive()
        print(f"Received: {self.metadata}")
        self.port = 8309
        print(f"UDP Port: {self.port}")
        self.send(f"200 Parameters Accepted. Use UDP port {self.port}\n")

    def process_command(self):
        print("Process Command")
        while True:
            command = self.receive()
            print(f'Received: {command}')
            if command is None:
         #       self.data_server.shutdown()
                break
            elif command.startswith('PING'):
                self.send(f'201 PING\n')
            elif command.startswith('DISCONNECT'):
               self.send(f'200 DISCONNECT')
        #       self.data_server.shutdown()
               break

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 8084

    # Create the server, binding to localhost on port 9999
    with ThreadedTCPServer((HOST, PORT), StreamTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()

