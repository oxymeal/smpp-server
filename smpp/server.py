import asyncio
import struct
from collections import defaultdict
from enum import Enum

from . import parse, messaging


class Mode(Enum):
    UNBOUND = 0
    RECEIVER = 1
    TRANSMITTER = 2
    TRANSCEIVER = 3


class Connection:
    def __init__(self, r: asyncio.StreamReader, w: asyncio.StreamWriter,
                 client: 'Client' = None):
        self.mode = Mode.UNBOUND
        self.client = client
        self.r = r
        self.w = w

    def __repr__(self) -> str:
        return "Connection({})".format(self.mode)


class BoundResponseSender:
    def __init__(self, server: 'Server', conn: Connection):
        self.server = server
        self.conn = conn

    async def send(self, pdu: parse.PDU):
        try:
            pdu_bytes = pdu.pack()
        except parse.PackingError:
            if pdu.command == parse.Command.GENERIC_NACK:
                raise

            nack = parse.GenericNack()
            nack.sequence_number = pdu.sequence_number
            nack.command_status = parse.COMMAND_STATUS_ESME_RUNKNOWNERR
            await self.send(nack)
            return

        self.conn.w.write(pdu_bytes)
        await self.conn.w.drain()


class Client:
    def __init__(self, system_id: str, password: str):
        self.system_id = system_id
        self.password = password
        self.connections = set()
        self._mdispatcher = messaging.Dispatcher(
            self.system_id, self.password, None)

    def __repr__(self) -> str:
        return "Client('{}', {})".format(self.system_id, self.connections)


class Server:
    def __init__(self, host='0.0.0.0', port=2775):
        self.host = host
        self.port = port

        # Maps system_ids to client objects.
        self._clients = {} # type: Dict[str, Client]

    def _bind(self, conn: Connection, m: Mode, sid: str, pwd: str):
        self._unbind(conn)

        if sid not in self._clients:
            self._clients[sid] = Client(sid, pwd)

        self._clients[sid].connections.add(conn)
        conn.mode = m
        conn.client = self._clients[sid]

    def _unbind(self, conn: Connection):
        conn.mode = Mode.UNBOUND
        conn.client = None

        remove_sids = set()
        for sid, client in self._clients.items():
            if conn in client.connections:
                client.connections.remove(conn)

            if len(client.connections) == 0:
                remove_sids.add(sid)

        for sid in remove_sids:
            del self._clients[sid]

    async def _dispatch_pdu(self, brs: BoundResponseSender, pdu: parse.PDU):
        if pdu.command == parse.Command.ENQUIRE_LINK:
            resp = parse.EnquireLinkResp()
            resp.sequence_number = pdu.sequence_number
            await brs.send(resp)
            return
        elif pdu.command == parse.Command.BIND_RECEIVER:
            self._bind(brs.conn, Mode.RECEIVER, pdu.system_id, pdu.password)
            resp = parse.BindReceiverResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await brs.send(resp)
            return
        elif pdu.command == parse.Command.BIND_TRANSMITTER:
            self._bind(brs.conn, Mode.TRANSMITTER, pdu.system_id, pdu.password)
            resp = parse.BindTransmitterResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await brs.send(resp)
            return
        elif pdu.command == parse.Command.BIND_TRANSCEIVER:
            self._bind(brs.conn, Mode.TRANSCEIVER, pdu.system_id, pdu.password)
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
        brs = BoundResponseSender(self, conn)

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
                    nack = parse.GenericNack()
                    nack.sequence_number = 0
                    nack.command_status = parse.COMMAND_STATUS_ESME_RUNKNOWNERR
                    await brs.send(nack)
                    continue

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
