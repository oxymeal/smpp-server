import asyncio
import struct
from collections import defaultdict
from enum import Enum

from . import parse


class Mode(Enum):
    UNBOUND = 0
    RECEIVER = 1
    TRANSMITTER = 2
    TRANSCEIVER = 3


class Connection:
    def __init__(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        self.mode = Mode.UNBOUND
        self.system_id = None
        self.r = r
        self.w = w

    def __repr__(self) -> str:
        return "Connection({}, {})".format(self.mode, self.system_id)


class BoundResponseSender:
    def __init__(self, server: 'Server', conn: Connection):
        self.server = server
        self.conn = conn

    async def send(self, pdu: parse.PDU):
        try:
            pdu_bytes = pdu.pack()
        except parse.PackingError:
            # TODO: Return g-back
            raise

        self.conn.w.write(pdu_bytes)
        await self.conn.w.drain()


class Server:
    def __init__(self, host='0.0.0.0', port=2775):
        self.host = host
        self.port = port

        # Maps system_ids to connections.
        self._connections = defaultdict(set) # type: Dict[int, Set[Connection]]

    def _bind(self, conn: Connection, m: Mode, sid: int):
        conn.mode = m
        conn.system_id = sid
        self._connections[sid].add(conn)

    def _unbind(self, conn: Connection):
        conn.mode = Mode.UNBOUND
        conn.system_id = None

        remove_sids = set()
        for sid, _conns in self._connections.items():
            if conn in _conns:
                _conns.remove(conn)

            if len(_conns) == 0:
                remove_sids.add(sid)

        for sid in remove_sids:
            del self._connections[sid]

    async def _dispatch_pdu(self, brs: BoundResponseSender, pdu: parse.PDU):
        if pdu.command == parse.Command.ENQUIRE_LINK:
            resp = parse.EnquireLinkResp()
            resp.sequence_number = pdu.sequence_number
            await brs.send(resp)
            return
        elif pdu.command == parse.Command.BIND_RECEIVER:
            self._bind(brs.conn, Mode.RECEIVER, pdu.system_id)
            resp = parse.BindReceiverResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await brs.send(resp)
            return
        elif pdu.command == parse.Command.BIND_TRANSMITTER:
            self._bind(brs.conn, Mode.TRANSMITTER, pdu.system_id)
            resp = parse.BindTransmitterResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await brs.send(resp)
            return
        elif pdu.command == parse.Command.BIND_TRANSCEIVER:
            self._bind(brs.conn, Mode.TRANSCEIVER, pdu.system_id)
            resp = parse.BindTransceiverResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await brs.send(resp)
            return
        elif pdu.command == parse.Command.UNBIND:
            self._unbind(brs.conn)
            resp = parse.UnbindResp()
            resp.sequence_number = pdu.sequence_number
            await brs.send(resp)
            return
        raise NotImplementedError('not yet implemented for other commands')

    async def _on_client_connected(self, conn: Connection):
        try:
            while True:
                pdu_len_b = await conn.r.readexactly(4)
                if not pdu_len_b:
                    break

                pdu_len, = struct.unpack("!I", pdu_len_b)

                pdu_body = await conn.r.readexactly(pdu_len - 4)
                if not pdu_body or len(pdu_body) < pdu_len - 4:
                    break

                pdu_bytes = pdu_len_b + pdu_body

                try:
                    pdu = parse.unpack_pdu(pdu_bytes)
                except parse.UnpackingError:
                    # TODO: Return g-nack
                    raise

                brs = BoundResponseSender(self, conn)
                await self._dispatch_pdu(brs, pdu)

        except asyncio.IncompleteReadError:
            pass

        conn.w.close()
        self._unbind(conn)


    async def start(self):
        async def conncb(r: asyncio.StreamReader, w: asyncio.StreamWriter):
            conn = Connection(r, w)
            await self._on_client_connected(conn)

        await asyncio.start_server(conncb, self.host, self.port)

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        loop.run_forever()
