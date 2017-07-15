import asyncio
import struct


class Server:
    def __init__(self, host='0.0.0.0', port=2775):
        self.host = host
        self.port = port

    async def _on_client_connected(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        try:
            while True:
                pdu_len_b = await r.readexactly(4)
                if not pdu_len_b:
                    w.close()
                    return

                pdu_len, = struct.unpack("!I", pdu_len_b)

                pdu_body = await r.readexactly(pdu_len - 4)
                if not pdu_body or len(pdu_body) < pdu_len - 4:
                    w.close()
                    return

                pdu = pdu_len_b + pdu_body

                print("Read pdu", len(pdu), "bytes long:", pdu)
        except asyncio.IncompleteReadError:
            w.close()
            return


    async def start(self):
        await asyncio.start_server(self._on_client_connected, self.host, self.port)

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        loop.run_forever()
