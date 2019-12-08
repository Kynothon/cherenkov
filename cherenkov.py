#! /usr/bin/env python3
import argparse
import hashlib
import logging
import asyncio
import enum
import hmac

class Stream:
    def __init__(self, reader, writer, logger):
        # TODO: Make port random
        self.port = 8309
        self.reader = reader
        self.writer = writer
        self.logger = logger

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
            # TODO: Do Not hardcode the values
            signature = hmac.new("secret".encode(), "body".encode(), digestmod=hashlib.sha512).hexdigest()
            self.logger.info(f"HMAC: {signature}")
            self.writer.write(f"200 {signature}\n".encode())
        elif message.startswith("DISCONNECT"):
            self.writer.write(f"200 DISCONNECT\n".encode())
        else:
            raise Exception("Expected HMAC")

    async def connect(self):
        message = await self.read()
        if message.startswith("CONNECT"):
            # TODO: Do something with the connection data CONNECT[ ]<STREAM_KEY_PREFIX>[]$???
            self.logger.info(f"CONNECTION Accepted {' '.join(message.split()[1:])}")
            self.writer.write(f"200 Accepted, go ahead with stream metadata\n".encode())
        elif message.startswith("DISCONNECT"):
            self.writer.write(f"200 DISCONNECT\n".encode())
        else:
            raise Exception("Expected CONNECT")

    async def stream_config(self):
        while True:
            message = await self.read()
            isEnd = any(item.startswith('.') for item in message.splitlines())
            # TODO: Parse the metadata
            self.logger.info(f"stream metadata: \"{message}\"")
            if isEnd:
                self.logger.info("Received all metatada")
                self.writer.write(f"200 Parameters Accepted. Use UDP port {self.port}\n".encode())
                break

    async def keepalive(self):
        while True:
            message = await self.read()
            if message.startswith("PING"):
                # TODO: Verify PING value matches stream key prefix
                # TODO: Add timeout 
                self.logger.info("Ping")
                self.writer.write("201 PING\n".encode())
            elif message.startswith("DISCONNECT"):
                self.writer.write(f"200 DISCONNECT\n".encode())
            elif len(message) == 0:
                raise EOFError()
            else:
                raise Exception("PING failure")


    async def idk(self):
        message = await self.read()
        print(f"message: {message}")
        raise Exception("blip")

class Signalling:
    def __init__(self, address = "0.0.0.0", port=8084, logger=None):
        self.address = address
        self.port = port
        self.logger = logger

    async def handle_stream(self, reader, writer):
        addr = writer.get_extra_info('peername')
        session = Stream(reader, writer, self.logger)

        try:
            print(f"Opening connection with {addr}")
            await session.hmac()
            await session.connect()
            await session.stream_config()
            await session.keepalive()
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


class Server:
    def __init__(self, args):
        self.port = args.port
        self.verbose = args.verbose
        self.logger = logging.getLogger()
        if self.verbose:
            logging.basicConfig(level=logging.DEBUG)
        self.logger.debug("logging level: verbose")

    async def run(self):
        await Signalling(port = self.port, logger=self.logger).run()

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
