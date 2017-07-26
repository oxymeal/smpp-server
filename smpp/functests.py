import time
import socket
import unittest
import re
import threading
from typing import List

from smpp import external
from smpp.server import Server
from smpp.vendor.smpplib import consts
from smpp.vendor.smpplib.client import Client
from smpp.vendor.smpplib.exceptions import PDUError
from smpp.vendor.smpplib.smpp import make_pdu
from timeout_decorator import timeout


import logging
logging.basicConfig(level=logging.ERROR)


TEST_SERVER_PORT = 2775


def start_server_thread(unix_sock=None, **kwargs):
    if unix_sock:
        server = Server(unix_sock=unix_sock, **kwargs)
    else:
        server = Server(port=TEST_SERVER_PORT, **kwargs)

    sproc = threading.Thread(target=server.run)
    sproc.start()

    # Wait for port to open

    if unix_sock:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    CONNECTION_TIMEOUT = 2
    RETRIES_INTERVAL = 0.1

    waiting_time = 0
    while True:
        if unix_sock:
            res = s.connect_ex(unix_sock)
        else:
            res = s.connect_ex(('localhost', TEST_SERVER_PORT))

        if res == 0:
            s.close()
            break

        waiting_time += RETRIES_INTERVAL
        if waiting_time > CONNECTION_TIMEOUT:
            s.close()
            raise RuntimeError("Server did not start")

        time.sleep(RETRIES_INTERVAL)

    return server, sproc


class EnquireLinkTestCase(unittest.TestCase):
    def setUp(self):
        self.server, self.sthread = start_server_thread()

    def tearDown(self):
        self.server.stop()
        self.sthread.join()

    def test_enquire_link_resp(self):
        client = Client('localhost', TEST_SERVER_PORT, timeout=1)
        client.connect()

        command = make_pdu('enquire_link', client=client)
        client.send_pdu(command)
        resp = client.read_pdu()

        self.assertEqual(resp.command, 'enquire_link_resp')
        self.assertEqual(resp.sequence, command.sequence)

        client.disconnect()


class BindStatusCheckingTestCase(unittest.TestCase):
    def setUp(self):
        self.server, self.sthread = start_server_thread()

    def tearDown(self):
        self.server.stop()
        self.sthread.join()

    def test_nobind_nack(self):
        client = Client('localhost', TEST_SERVER_PORT, timeout=1)
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
        client = Client('localhost', TEST_SERVER_PORT, timeout=1)
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
        self.server, self.sthread = start_server_thread()

    def tearDown(self):
        self.server.stop()
        self.sthread.join()

    @timeout(seconds=1)
    def test_async_eqlinks(self):
        c1 = Client('localhost', TEST_SERVER_PORT, timeout=1)
        c1.connect()
        cmd1 = make_pdu('enquire_link', client=c1)
        cmd1.sequence = 1
        c1.send_pdu(cmd1)

        c2 = Client('localhost', TEST_SERVER_PORT, timeout=1)
        c2.connect()
        cmd2 = make_pdu('enquire_link', client=c2)
        cmd2.sequence = 2
        c2.send_pdu(cmd2)

        c3 = Client('localhost', TEST_SERVER_PORT, timeout=1)
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


class BindAuthTestCase(unittest.TestCase):
    class DummyProvider:
        def __init__(self, csid: str, cpwd: str):
            self.csid = csid
            self.cpwd = cpwd

        async def authenticate(self, system_id: str, password: str) -> bool:
            return self.csid == system_id and self.cpwd == password


    CORRECT_SID = "user"
    CORRECT_PWD = "mypwd"
    INCORRECT_SID = "user2"
    INCORRECT_PWD = "mypwd2"


    def setUp(self):
        self.server, self.sthread = start_server_thread(
            provider=self.DummyProvider(self.CORRECT_SID, self.CORRECT_PWD))

    def tearDown(self):
        self.server.stop()
        self.sthread.join()

    def test_auth_bind(self):
        client = Client('localhost', TEST_SERVER_PORT, timeout=1)
        client.connect()

        # Should not raise
        client.bind_transmitter(
            system_id=self.CORRECT_SID, password=self.CORRECT_PWD)

    def test_unauth_bind(self):
        client = Client('localhost', TEST_SERVER_PORT, timeout=1)
        client.connect()

        with self.assertRaises(PDUError):
            client.bind_transmitter(
                system_id=self.INCORRECT_SID, password=self.CORRECT_PWD)

        with self.assertRaises(PDUError):
            client.bind_transmitter(
                system_id=self.CORRECT_SID, password=self.INCORRECT_PWD)

        with self.assertRaises(PDUError):
            client.bind_transmitter(
                system_id=self.INCORRECT_SID, password=self.INCORRECT_PWD)


class UnixSocketTestCase(unittest.TestCase):
    UNIX_SOCK = '/tmp/smpp_server_functest_server.sock'

    def setUp(self):
        self.server, self.sthread = start_server_thread(unix_sock=self.UNIX_SOCK)

    def tearDown(self):
        self.server.stop()
        self.sthread.join()

    def test_unix_sock_enquire_link(self):
        # Simple sanity test
        client = Client(unix_sock=self.UNIX_SOCK)
        client.connect()

        elink = make_pdu('enquire_link', client=client)
        elink.sequence = 1
        client.send_pdu(elink)

        elink_resp = client.read_pdu()
        self.assertEqual(elink_resp.sequence, elink.sequence)


class MessagingTestCase(unittest.TestCase):
    class DummyProvider:
        def __init__(self):
            self.status = external.DeliveryStatus.OK
            self.mlock = threading.Lock()
            self.msem = threading.Semaphore(0)
            self.messages = []

        async def authenticate(self, system_id: str, password: str) -> bool:
            return True

        async def deliver(self, sm: external.ShortMessage) -> external.DeliveryStatus:
            with self.mlock:
                self.messages.append(sm)

            self.msem.release()

            return self.status

        def wait_for_message(self, timeout=None):
            self.msem.acquire(timeout=timeout)

        def get_messages(self) -> List[external.ShortMessage]:
            with self.mlock:
                return self.messages

    def setUp(self):
        self.provider = self.DummyProvider()
        self.server, self.sthread = start_server_thread(provider=self.provider)

    def tearDown(self):
        self.server.stop()
        self.sthread.join()

    def test_store_and_forward(self):
        t = Client('localhost', TEST_SERVER_PORT, timeout=1)
        t.connect()
        t.bind_transmitter(system_id="mtc", password="pwd")

        message_text = "Hello world!"

        ssm = t.send_message(
            esm_class=consts.SMPP_MSGMODE_STOREFORWARD,
            registered_delivery=0b11100001, # Request delivery receipt with noise bits
            source_addr_ton=12,
            source_addr_npi=34,
            source_addr="src",
            dest_addr_ton=56,
            dest_addr_npi=67,
            destination_addr="dst",
            short_message=message_text.encode('ascii'))

        ssmr = t.read_pdu()
        self.assertEqual(ssmr.command, 'submit_sm_resp')
        self.assertEqual(ssmr.sequence, ssm.sequence)

        self.provider.wait_for_message(timeout=1)

        messages = self.provider.get_messages()
        self.assertEqual(len(messages), 1)

        msg = messages[0]
        self.assertEqual(msg.system_id, "mtc")
        self.assertEqual(msg.password, "pwd")
        self.assertEqual(msg.source_addr_ton, 12)
        self.assertEqual(msg.source_addr_npi, 34)
        self.assertEqual(msg.source_addr, "src")
        self.assertEqual(msg.dest_addr_ton, 56)
        self.assertEqual(msg.dest_addr_npi, 67)
        self.assertEqual(msg.destination_addr, "dst")
        self.assertEqual(msg.body, message_text)

    def test_receipt_delivery(self):
        t = Client('localhost', TEST_SERVER_PORT, timeout=1)
        t.connect()
        t.bind_transmitter(system_id="mtc", password="pwd")

        r1 = Client('localhost', TEST_SERVER_PORT, timeout=1)
        r1.connect()
        r1.bind_receiver(system_id="mtc", password="pwd")

        r2 = Client('localhost', TEST_SERVER_PORT, timeout=1)
        r2.connect()
        r2.bind_receiver(system_id="mtc", password="pwd")

        rx = Client('localhost', TEST_SERVER_PORT, timeout=1)
        rx.connect()
        rx.bind_receiver(system_id="nomtc", password="pwd")

        message_text = "Hello world!"

        ssm = t.send_message(
            esm_class=consts.SMPP_MSGMODE_STOREFORWARD,
            registered_delivery=0b11100001, # Request delivery receipt with noise bits
            source_addr_ton=12,
            source_addr_npi=34,
            source_addr="src",
            dest_addr_ton=56,
            dest_addr_npi=67,
            destination_addr="dst",
            short_message=message_text.encode('ascii'))

        r1rec = r1.read_pdu()
        self.assertEqual(r1rec.command, 'deliver_sm')
        self.assertNotEqual(int(r1rec.esm_class) & 0b00000100, 0)

        r2rec = r2.read_pdu()
        self.assertEqual(r2rec.command, 'deliver_sm')
        self.assertNotEqual(int(r2rec.esm_class) & 0b00000100, 0)

        with self.assertRaises(socket.timeout):
            rx.read_pdu()

    def test_successful_receipt(self):
        t = Client('localhost', TEST_SERVER_PORT, timeout=1)
        t.connect()
        t.bind_transmitter(system_id="mtc", password="pwd")

        r1 = Client('localhost', TEST_SERVER_PORT, timeout=1)
        r1.connect()
        r1.bind_receiver(system_id="mtc", password="pwd")

        message_text = "Hello world!"

        ssm = t.send_message(
            esm_class=consts.SMPP_MSGMODE_STOREFORWARD,
            registered_delivery=0b11100001, # Request delivery receipt with noise bits
            source_addr_ton=12,
            source_addr_npi=34,
            source_addr="src",
            dest_addr_ton=56,
            dest_addr_npi=67,
            destination_addr="dst",
            short_message=message_text.encode('ascii'))

        ssmr = t.read_pdu()

        receipt_regex = r'^id:(\S+) sub:(\d+) dlvrd:(\d+) submit date:(\d+) done date:(\d+) stat:(\S+) err:(\d+) text:(.+)$'

        rec = r1.read_pdu()
        self.assertEqual(rec.command, 'deliver_sm')
        self.assertNotEqual(int(rec.esm_class) & 0b00000100, 0)

        m = re.search(receipt_regex, rec.short_message.decode('ascii'))
        self.assertIsNotNone(m, msg="Receipt text does not match regex")

        rct_id, _, rct_dlvr, _, _, rct_stat, rct_err, rct_text = m.groups()
        self.assertEqual(rct_id, ssmr.message_id.decode('ascii'))
        self.assertEqual(int(rct_dlvr), 1)
        self.assertEqual(rct_stat, 'DELIVRD')
        self.assertEqual(int(rct_err), 0)
        self.assertTrue(message_text.startswith(rct_text))

    def _test_error_receipt(self, prov_status: external.DeliveryStatus, exp_rct_status: str):
        self.provider.status = prov_status

        t = Client('localhost', TEST_SERVER_PORT, timeout=1)
        t.connect()
        t.bind_transmitter(system_id="mtc", password="pwd")

        r1 = Client('localhost', TEST_SERVER_PORT, timeout=1)
        r1.connect()
        r1.bind_receiver(system_id="mtc", password="pwd")

        message_text = "Hello world!"

        ssm = t.send_message(
            esm_class=consts.SMPP_MSGMODE_STOREFORWARD,
            registered_delivery=0b11100010, # Request delivery receipt with noise bits
            source_addr_ton=12,
            source_addr_npi=34,
            source_addr="src",
            dest_addr_ton=56,
            dest_addr_npi=67,
            destination_addr="dst",
            short_message=message_text.encode('ascii'))

        ssmr = t.read_pdu()

        receipt_regex = r'^id:(\S+) sub:(\d+) dlvrd:(\d+) submit date:(\d+) done date:(\d+) stat:(\S+) err:(\d+) text:(.+)$'

        rec = r1.read_pdu()
        self.assertEqual(rec.command, 'deliver_sm')
        self.assertNotEqual(int(rec.esm_class) & 0b00000100, 0)

        m = re.search(receipt_regex, rec.short_message.decode('ascii'))
        self.assertIsNotNone(m, msg="Receipt text does not match regex")

        rct_id, _, rct_dlvr, _, _, rct_stat, rct_err, rct_text = m.groups()
        self.assertEqual(rct_id, ssmr.message_id.decode('ascii'))
        self.assertEqual(int(rct_dlvr), 0)
        self.assertEqual(rct_stat, exp_rct_status)
        self.assertEqual(int(rct_err), 1)
        self.assertTrue(message_text.startswith(rct_text))

    def test_error_receipts(self):
        self._test_error_receipt(external.DeliveryStatus.GENERIC_ERROR, 'EXPIRED')
        self._test_error_receipt(external.DeliveryStatus.TRY_LATER, 'EXPIRED')

        self._test_error_receipt(external.DeliveryStatus.AUTH_FAILED, 'REJECTD')
        self._test_error_receipt(external.DeliveryStatus.NO_BALANCE, 'REJECTD')

        self._test_error_receipt(external.DeliveryStatus.UNDELIVERABLE, 'UNDELIV')

    def test_no_success_receipt_required(self):
        t = Client('localhost', TEST_SERVER_PORT, timeout=1)
        t.connect()
        t.bind_transmitter(system_id="mtc", password="pwd")

        r1 = Client('localhost', TEST_SERVER_PORT, timeout=1)
        r1.connect()
        r1.bind_receiver(system_id="mtc", password="pwd")

        message_text = "Hello world!"

        ssm = t.send_message(
            esm_class=consts.SMPP_MSGMODE_STOREFORWARD,
            registered_delivery=0b11100010, # Request delivery receipt on failure only
            source_addr_ton=12,
            source_addr_npi=34,
            source_addr="src",
            dest_addr_ton=56,
            dest_addr_npi=67,
            destination_addr="dst",
            short_message=message_text.encode('ascii'))

        with self.assertRaises(socket.timeout):
            r1.read_pdu()
