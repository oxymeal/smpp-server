import unittest
import multiprocessing

from smpp.vendor.smpplib.client import Client
from smpp.vendor.smpplib.smpp import make_pdu
from smpp.server import Server


import logging
logging.basicConfig(level=logging.DEBUG)


class EnquireLinkTestCase(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.sproc = multiprocessing.Process(target=self.server.run)
        self.sproc.start()
        import time
        time.sleep(1)

    def tearDown(self):
        self.sproc.terminate()

    def test_enquire_link_resp(self):
        client = Client('localhost', 2775)
        client.connect()
        client.bind_transmitter()

        command = make_pdu('enquire_link', client=client)
        client.send_pdu(command)
        resp = client.read_pdu()

        self.assertEqual(resp.command, 'enquire_link_resp')
        self.assertEqual(resp.sequence, command.sequence)

        client.disconnect()
