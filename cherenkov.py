#! /usr/bin/env python3
import argparse
import hashlib
import logging
import asyncio
import secrets
import random
import enum
import hmac

keys = {'118403022': 'jHoiulkMZ80oGIvLwZCNsSu4DVR70zS4'}

class Stream:
    def __init__(self, reader, writer, logger):
        # TODO: Make port random
        self.media_port = random.randrange(8300, 8399)
        self.timeout = 10.0
        self.reader = reader
        self.writer = writer
        self.logger = logger
        self.stream_kid = ""
        self.metadata = {}

    async def read(self):
        message = ""
        while True:
            data = await self.reader.read(1024)
            if len(data) == 0:
                break
            message = message + data.decode()
            if message.endswith("\r\n\r\n"):
                break
        return message.strip()

    async def hmac(self):
        message = await self.read()
        if message.startswith("HMAC"):
            self.nonce = secrets.token_hex(64)
            self.logger.info(f"nonce: {self.nonce}")
            self.writer.write(f"200 {self.nonce}\n".encode())
        elif message.startswith("DISCONNECT"):
            self.writer.write(f"200 DISCONNECT\n".encode())
        else:
            raise Exception("Expected HMAC")

    def get_stream_key(self, stream_kid):
        return keys[stream_kid]

    async def connect(self):
        message = await self.read()
        if message.startswith("CONNECT"):
            parsed = message.split(' ')
            digest = hmac.new(self.get_stream_key(parsed[1]).encode(), 
            bytes.fromhex(self.nonce), 
            digestmod=hashlib.sha512).hexdigest()
            if parsed[2][1:] != digest:
                self.logger.error("mismatch signature")
                self.writer.write("401 STREAM REJECTED\n".encode())
                raise Exception("Mismatched signature")
            else:
                self.stream_kid = parsed[1]
                self.logger.info(f"CONNECTION Accepted {' '.join(parsed[1:])}")
                self.writer.write(f"200 Accepted, go ahead with stream metadata\n".encode())
        elif message.startswith("DISCONNECT"):
            self.writer.write(f"200 DISCONNECT\n".encode())
        else:
            raise Exception("Expected CONNECT")

    async def stream_config(self):
        isEnd = False
        while not isEnd:
            message = await self.read()
            for line in message.splitlines():
                parsed = line.split(':')
                if line.startswith('.'):
                    isEnd = True
                elif len(parsed) == 2:
                    self.metadata[parsed[0]] = parsed[1].strip()
        self.logger.info(f"Received all metatada: {self.metadata}")
        self.logger.info(f"Ready to receive data on UDP {self.media_port}")
        self.writer.write(f"200 Parameters Accepted. Use UDP port {self.media_port}\n".encode())

    async def keepalive(self):
        while True:
            message = await asyncio.wait_for(self.read(), timeout=self.timeout)
            if message.startswith("PING"):
                prefix = message[len("PING "):]
                self.logger.info(f"Ping {prefix}")
                self.writer.write("201 PING\n".encode())
            elif message.startswith("DISCONNECT"):
                self.writer.write(f"200 DISCONNECT\n".encode())
            elif len(message) == 0:
                raise EOFError()
            else:
                raise Exception("PING failure")

class Server:
    def __init__(self, args):
        self.port = args.port
        self.address = "0.0.0.0"
        self.verbose = args.verbose
        self.logger = logging.getLogger()
        if self.verbose:
            logging.basicConfig(level=logging.DEBUG)
        self.logger.debug("logging level: verbose")

    async def handle_stream(self, reader, writer):
        addr = writer.get_extra_info('peername')
        session = Stream(reader, writer, self.logger)

        try:
            print(f"Opening connection with {addr}")
            await session.hmac()
            await session.connect()
            await session.stream_config()
            await session.keepalive()
        except EOFError:
            self.logger.warning(f"Client {addr} terminated connection")
        except asyncio.TimeoutError:
            self.logger.warning(f"Client {addr} missed the timeout")
        except Exception as exeption: 
            print(f"Received Exception: {exeption}")
        finally:
            await writer.drain()
            print("Close the connection")
            writer.close()

    async def run(self):
        server = await asyncio.start_server(
            self.handle_stream, self.address, self.port)

        addr = server.sockets[0].getsockname()
        print(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

def uint16(value):
    ivalue = int(value)
    if ivalue < 0 or ivalue > 65535:
        raise argparse.ArgumentTypeError(f"{ivalue} is an invalid unsigned short int value")
    return ivalue

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", help="increase output verbosity",
                    action="store_true")
    parser.add_argument("-p", "--port", 
                    help="Specifies the port on which the server listens for connections (default 8084)",
                    type=uint16,
                    default=8084)
    args = parser.parse_args()
    server = Server(args)
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
