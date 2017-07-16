import asyncio
import struct


class Connection:
    def __init__(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        self.r = r
        self.w = w


class Server:
    def __init__(self, host='0.0.0.0', port=2775):
        self.host = host
        self.port = port

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
            conn.w.close()
            return


    async def start(self):
        async def conncb(r: asyncio.StreamReader, w: asyncio.StreamWriter):
            conn = Connection(r, w)
            await self._on_client_connected(conn)

        await asyncio.start_server(conncb, self.host, self.port)

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        loop.run_forever()
