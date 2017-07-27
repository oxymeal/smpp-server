#!/usr/bin/env python3
import logging
import random
from enum import Enum

from smpp.server import Server
from smpp.external import logging as ext_logging


logging.basicConfig(level=logging.DEBUG)


s = Server(provider=ext_logging.Provider(file_path='container/sms.txt'))
s.run()
