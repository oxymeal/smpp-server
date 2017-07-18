import logging
from smpp.server import Server

logging.basicConfig(level=logging.DEBUG)

s = Server()
s.run()
