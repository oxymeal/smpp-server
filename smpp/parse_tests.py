import unittest

from .parse import *


class ParserTestCase(unittest.TestCase):
    def test_unpack_enquire_link(self):

        h = b'\x00\x00\x00\x10\x00\x00\x00\x15\x00\x00\x00\x00\x00\x00\x00\x01'

        pdu = unpack_pdu(h)

        size = struct.calcsize("!IIII")
        cl, cid, cs, sn = struct.unpack("!IIII", h)

        self.assertEqual(pdu.command, Command(cid))
        self.assertEqual(pdu.command_id, cid)
        self.assertEqual(pdu.command_length, cl)
        self.assertEqual(pdu.command_status, cs)
        self.assertEqual(pdu.sequence_number, sn)

    def test_unpack_bind_transmitter(self):
        h = b"\x00\x00\x00'\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x02sys_id\x00pwd\x00type\x004\x16+adr\x00"

        size = struct.calcsize("!IIII")
        cl, cid, cs, sn = struct.unpack("!IIII", h[:size])
        system_id = 'sys_id'
        password = 'pwd'
        system_type = 'type'
        interface_version = '34'
        addr_ton = 22
        addr_npi = 43
        address_range = 'adr'

        pdu = unpack_pdu(h)

        self.assertEqual(pdu.command, Command(cid))
        self.assertEqual(pdu.command_id, cid)
        self.assertEqual(pdu.command_length, cl)
        self.assertEqual(pdu.command_status, cs)
        self.assertEqual(pdu.sequence_number, sn)
        self.assertEqual(pdu.system_id, system_id)
        self.assertEqual(pdu.password, password)
        self.assertEqual(pdu.system_type, system_type)
        self.assertEqual(pdu.interface_version, int(interface_version, 16))
        self.assertEqual(pdu.addr_ton, addr_ton)
        self.assertEqual(pdu.addr_npi, addr_npi)
        self.assertEqual(pdu.address_range, address_range)

    def test_submit_sm_unpack(self):

        h = b"\x00\x00\x00;\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x0b88005553535\x00\x00\x00\x00\x01\xdd\x0111\x0011\x00\x17\x02\x01\x00\x0bHello world"

        pdu = unpack_pdu(h)
        self.assertEqual(pdu.sequence_number, 1)
        self.assertEqual(pdu.source_addr_ton, 0)
        self.assertEqual(pdu.source_addr, "88005553535")
        self.assertEqual(pdu.esm_class, 1)
        self.assertEqual(pdu.protocol_id, 221)
        self.assertEqual(pdu.priority_flag, 1)
        self.assertEqual(pdu.schedule_delivery_time, "11")
        self.assertEqual(pdu.validity_period, "11")
        self.assertEqual(pdu.registered_delivery, 23)
        self.assertEqual(pdu.replace_if_present_flag, 2)
        self.assertEqual(pdu.data_coding, 1)
        self.assertEqual(pdu.sm_default_msg_id, 0)
        self.assertEqual(pdu.short_message, "Hello world")
