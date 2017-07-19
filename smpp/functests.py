import time
import socket
import unittest
import multiprocessing

from smpp.vendor.smpplib import consts
from smpp.vendor.smpplib.client import Client
from smpp.vendor.smpplib.smpp import make_pdu
from smpp.server import Server


import logging
logging.basicConfig(level=logging.CRITICAL)


TEST_SERVER_PORT = 2775


def start_server_proc():
    server = Server(port=TEST_SERVER_PORT)
    sproc = multiprocessing.Process(target=server.run)
    sproc.start()

    # Wait for port to opet
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        res = s.connect_ex(('localhost', TEST_SERVER_PORT))
        if res == 0:
            s.close()
            break

        time.sleep(0.1)

    return sproc

class EnquireLinkTestCase(unittest.TestCase):
    def setUp(self):
        self.sproc = start_server_proc()

    def tearDown(self):
        self.sproc.terminate()

    def test_enquire_link_resp(self):
        client = Client('localhost', TEST_SERVER_PORT)
        client.connect()

        command = make_pdu('enquire_link', client=client)
        client.send_pdu(command)
        resp = client.read_pdu()

        self.assertEqual(resp.command, 'enquire_link_resp')
        self.assertEqual(resp.sequence, command.sequence)

        client.disconnect()

class BindStatusCheckingTestCase(unittest.TestCase):
    def setUp(self):
        self.sproc = start_server_proc()

    def tearDown(self):
        self.sproc.terminate()

    def test_nobind_nack(self):
        client = Client('localhost', TEST_SERVER_PORT)
        client.connect()

        cmd = make_pdu('submit_sm', client=client,
                       source_addr_ton=12, source_addr="src",
                       dest_addr_ton=34, destination_addr="dst",
                       short_message=b"Hello world")
        client.send_pdu(cmd)
        resp = client.read_pdu()

        self.assertEqual(resp.command, 'generic_nack')
        self.assertEqual(resp.sequence, cmd.sequence)
        self.assertEqual(resp.status, consts.SMPP_ESME_RINVBNDSTS)

    def test_rcv_submit_nack(self):
        client = Client('localhost', TEST_SERVER_PORT)
        client.connect()
        client.bind_receiver()

        cmd = make_pdu('submit_sm', client=client,
                       source_addr_ton=12, source_addr="src",
                       dest_addr_ton=34, destination_addr="dst",
                       short_message=b"Hello world")
        client.send_pdu(cmd)
        resp = client.read_pdu()

        self.assertEqual(resp.command, 'generic_nack')
        self.assertEqual(resp.sequence, cmd.sequence)
        self.assertEqual(resp.status, consts.SMPP_ESME_RINVBNDSTS)
