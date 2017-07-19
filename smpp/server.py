import asyncio
import logging
import struct
from collections import defaultdict
from enum import Enum
from typing import Iterator, Optional, Tuple

from . import parse, messaging


logger = logging.getLogger(__name__)


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
        logger.debug('Sending {} for {} at {}'.format(
            pdu.command, self.system_id, self.peer))

        try:
            pdu_bytes = pdu.pack()
        except parse.PackingError as e:
            logger.error('Error packing {} for {} at {}: {}'.format(
                pdu.command, self.system_id, self.peer, e))

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
        logger.debug('Sending {} for all receivers of {}'.format(
            pdu.command, self.system_id))

        recvs = self.server.get_receivers(self.system_id)
        tasks = [c.send(pdu) for c in recvs]
        await asyncio.gather(*tasks)

    @property
    def peer(self) -> Tuple[str, int]:
        return self.w.get_extra_info('peername')

    @property
    def system_id(self) -> Optional[str]:
        if not self.client:
            return None

        return self.client.system_id

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
        logger.info('PDU {} from {}'.format(pdu.command, conn.peer))

        if pdu.command == parse.Command.ENQUIRE_LINK:
            resp = parse.EnquireLinkResp()
            resp.sequence_number = pdu.sequence_number
            await conn.send(resp)
            return
        elif pdu.command == parse.Command.BIND_RECEIVER:
            self._bind(conn, Mode.RECEIVER, pdu.system_id, pdu.password)
            logger.info('Bound {} at {} as RECEIVER'.format(conn.system_id, conn.peer))
            resp = parse.BindReceiverResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await conn.send(resp)
            return
        elif pdu.command == parse.Command.BIND_TRANSMITTER:
            self._bind(conn, Mode.TRANSMITTER, pdu.system_id, pdu.password)
            logger.info('Bound {} at {} as TRANSMITTER'.format(conn.system_id, conn.peer))
            resp = parse.BindTransmitterResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await conn.send(resp)
            return
        elif pdu.command == parse.Command.BIND_TRANSCEIVER:
            self._bind(conn, Mode.TRANSCEIVER, pdu.system_id, pdu.password)
            logger.info('Bound {} at {} as TRANSCEIVER'.format(conn.system_id, conn.peer))
            resp = parse.BindTransceiverResp()
            resp.sequence_number = pdu.sequence_number
            resp.system_id = pdu.system_id
            await conn.send(resp)
            return
        elif pdu.command == parse.Command.UNBIND:
            self._unbind(conn)
            logger.info('Unbound {}'.format(conn.peer))
            resp = parse.UnbindResp()
            resp.sequence_number = pdu.sequence_number
            await conn.send(resp)
            return

        if not conn.can_transmit():
            # TODO: Check the command.
            # Some receiver responses must be allowed here.
            logger.error('Invalid bind status ({}) for command {} from {} at {}'.format(
                conn.mode, pdu.command, conn.system_id, conn.peer))
            nack = parse.GenericNack()
            nack.sequence_number = pdu.sequence_number
            # Invalid bind status
            nack.command_status = parse.COMMAND_STATUS_ESME_RINVBNDSTS
            await conn.send(nack)
            return

        await conn.client.mdispatcher.receive(pdu, conn)

    async def _on_client_connected(self, conn: Connection):
        logger.info('New connection from {}'.format(conn.peer))

        try:
            while True:
                pdu_len_b = await conn.r.readexactly(4)
                if not pdu_len_b:
                    logger.debug(
                        'EOF while reading pdu length from {} at {}'.format(conn.system_id, conn.peer))
                    break

                pdu_len, = struct.unpack("!I", pdu_len_b)

                pdu_body = await conn.r.readexactly(pdu_len - 4)
                if not pdu_body or len(pdu_body) < pdu_len - 4:
                    logger.debug(
                        'EOF while reading pdu from {} at {}'.format(conn.system_id, conn.peer))
                    break

                pdu_bytes = pdu_len_b + pdu_body
                logger.debug('PDU in {} bytes received from {} at {}'.format(
                    len(pdu_bytes), conn.system_id, conn.peer))

                try:
                    pdu = parse.unpack_pdu(pdu_bytes)
                except parse.UnpackingError as e:
                    logger.error(
                        'Error while unpacking PDU bytes from {} at {}: {}'.format(
                            conn.peer, conn.system_id, e))
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

        logger.info("Starting SMPP server at {}:{}".format(self.host, self.port))
        await asyncio.start_server(conncb, self.host, self.port)

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        loop.run_forever()
