import asyncio
import struct
from collections import defaultdict
from enum import Enum


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

    async def _on_client_connected(self, conn: Connection):
        try:
            while True:
                pdu_len_b = await conn.r.readexactly(4)
                if not pdu_len_b:
                    w.close()
                    return

                pdu_len, = struct.unpack("!I", pdu_len_b)

                pdu_body = await conn.r.readexactly(pdu_len - 4)
                if not pdu_body or len(pdu_body) < pdu_len - 4:
                    w.close()
                    return

                pdu = pdu_len_b + pdu_body

                print("Read pdu", len(pdu), "bytes long:", pdu)
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
