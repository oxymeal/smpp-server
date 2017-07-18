import asyncio
import struct
from collections import defaultdict
from enum import Enum
from typing import Iterator, Tuple

from . import parse, messaging


class Mode(Enum):
    UNBOUND = 0
    RECEIVER = 1
    TRANSMITTER = 2
    TRANSCEIVER = 3


class Connection:
    def __init__(self, server: 'Server', r: asyncio.StreamReader, w: asyncio.StreamWriter,
                 client: 'Client' = None):
        self.server = server
        self.r = r
        self.w = w
        self.mode = Mode.UNBOUND
        self.client = client

    def __repr__(self) -> str:
        return "Connection({})".format(self.mode)

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

        self.w.write(pdu_bytes)
        await self.w.drain()

    async def send_to_rcv(self, pdu: parse.PDU):
        recvs = self.server.get_receivers(self.client.system_id)
        tasks = [c.send(pdu) for c in recvs]
        await asyncio.gather(*tasks)

    def can_transmit(self) -> bool:
        return self.mode in [Mode.TRANSMITTER, Mode.TRANSCEIVER]

    def can_receive(self) -> bool:
        return self.mode in [Mode.RECEIVER, Mode.TRANSCEIVER]


class Client:
    def __init__(self, system_id: str, password: str):
        self.system_id = system_id
        self.password = password
        self.connections = set()
        self.mdispatcher = messaging.Dispatcher(
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

    def get_receivers(self, sid: str) -> Iterator[Connection]:
        if sid not in self._clients:
            return

        for conn in self._clients[sid].connections:
            if conn.can_receive():
                yield conn

    async def _dispatch_pdu(self, conn: Connection, pdu: parse.PDU):
        if pdu.command == parse.Command.ENQUIRE_LINK:
            resp = parse.EnquireLinkResp()
            resp.sequence_number = pdu.sequence_number
            await conn.send(resp)
            return
        elif pdu.command == parse.Command.BIND_RECEIVER:
            self._bind(conn, Mode.RECEIVER, pdu.system_id, pdu.password)
            resp = parse.BindReceiverResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await conn.send(resp)
            return
        elif pdu.command == parse.Command.BIND_TRANSMITTER:
            self._bind(conn, Mode.TRANSMITTER, pdu.system_id, pdu.password)
            resp = parse.BindTransmitterResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await conn.send(resp)
            return
        elif pdu.command == parse.Command.BIND_TRANSCEIVER:
            self._bind(conn, Mode.TRANSCEIVER, pdu.system_id, pdu.password)
            resp = parse.BindTransceiverResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await conn.send(resp)
            return
        elif pdu.command == parse.Command.UNBIND:
            self._unbind(conn)
            resp = parse.UnbindResp()
            resp.sequence_number = pdu.sequence_number
            await conn.send(resp)
            return

        if not conn.can_transmit():
            # TODO: Check the command.
            # Some receiver responses must be allowed here.
            nack = parse.GenericNack()
            nack.sequence_number = pdu.sequence_number
            # Invalid bind status
            nack.command_status = parse.COMMAND_STATUS_ESME_RINVBNDSTS
            await conn.send(nack)
            return

        await conn.client.mdispatcher.receive(pdu, conn)

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
                    nack = parse.GenericNack()
                    nack.sequence_number = 0
                    nack.command_status = parse.COMMAND_STATUS_ESME_RUNKNOWNERR
                    await conn.send(nack)
                    continue

                await self._dispatch_pdu(conn, pdu)

        except asyncio.IncompleteReadError:
            pass

        conn.w.close()
        self._unbind(conn)


    async def start(self):
        async def conncb(r: asyncio.StreamReader, w: asyncio.StreamWriter):
            conn = Connection(self, r, w)
            await self._on_client_connected(conn)

        await asyncio.start_server(conncb, self.host, self.port)

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        loop.run_forever()
