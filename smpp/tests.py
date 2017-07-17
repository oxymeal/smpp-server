import unittest

from parse import *


class ParserTestCase(unittest.TestCase):
    def test_unpack_enquire_link(self):

        h = b'\x00\x00\x00\x10\x00\x00\x00\x15\x00\x00\x00\x00\x00\x00\x00\x01'
        inp = bytearray(h)

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
        inp = bytearray(h)

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


if __name__ == '__main__':
    unittest.main()
