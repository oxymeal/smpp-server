import time
import socket
import unittest
import multiprocessing

from smpp.vendor.smpplib import consts
from smpp.vendor.smpplib.client import Client
from smpp.vendor.smpplib.smpp import make_pdu
from smpp.server import Server
from timeout_decorator import timeout


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


class AsyncDispatchTestCase(unittest.TestCase):
    def setUp(self):
        self.sproc = start_server_proc()

    def tearDown(self):
        self.sproc.terminate()

    @timeout(seconds=1)
    def test_async_eqlinks(self):
        c1 = Client('localhost', TEST_SERVER_PORT)
        c1.connect()
        cmd1 = make_pdu('enquire_link', client=c1)
        cmd1.sequence = 1
        c1.send_pdu(cmd1)

        c2 = Client('localhost', TEST_SERVER_PORT)
        c2.connect()
        cmd2 = make_pdu('enquire_link', client=c2)
        cmd2.sequence = 2
        c2.send_pdu(cmd2)

        c3 = Client('localhost', TEST_SERVER_PORT)
        c3.connect()
        cmd3 = make_pdu('enquire_link', client=c3)
        cmd3.sequence = 3
        c3.send_pdu(cmd3)

        # Should not block
        resp3 = c3.read_pdu()
        resp1 = c1.read_pdu()
        resp2 = c2.read_pdu()

        # Should dispatch correctly
        self.assertEqual(resp1.sequence, 1)
        self.assertEqual(resp2.sequence, 2)
        self.assertEqual(resp3.sequence, 3)
