import asyncio
import logging
import multiprocessing
from collections import namedtuple
from typing import Callable, List

from smpp import external
from smpp.server import Server


logger = logging.getLogger(__name__)


class MasterServer:
    BUFFER_SIZE = 256

    def __init__(
        self,
        host: str = '0.0.0.0', port: int = 2775,
        build_provider: Callable[..., external.Provider] = None,
        workers_count: int = 1,
        worker_socket_template: str = '/tmp/smpp_server_{port}_worker_{i}.sock',
        incoming_queue_base_port: int = 25555):

        self.host = host
        self.port = port
        self.build_provider = build_provider
        self.workers_count = workers_count
        self.worker_socket_template = worker_socket_template
        self.incoming_queue_base_port = incoming_queue_base_port

        self.loop = None
        self._worker_procs = []
        # This variable is used for round-robin incoming connections balancing.
        self._last_used_worker = -1

    def _sock_for_worker(self, i: int) -> str:
        return self.worker_socket_template.format(
            port=self.port, i=i)

    def _queue_url_for_worker(self, i: int) -> str:
        return "tcp://127.0.0.1:{}".format(self.incoming_queue_base_port + i)

    def _all_queue_ports(self) -> List[int]:
        return [self.incoming_queue_base_port + i for i in range(self.workers_count)]

    def _all_queue_urls(self) -> List[str]:
        return [self._queue_url_for_worker(i) for i in range(self.workers_count)]

    def _run_worker_procs(self):
        logger.debug("Starting {} workers".format(self.workers_count))

        for i in range(self.workers_count):
            logger.debug("Worker #{} at '{}' publishing to '{}'".format(
                i, self._sock_for_worker(i), self._queue_url_for_worker(i)))

            server = Server(
                unix_sock=self._sock_for_worker(i),
                incoming_queue=self._queue_url_for_worker(i))

            if self.build_provider:
                p = self.build_provider(server=server)
                server.provider = p

            proc = multiprocessing.Process(
                target=server.run, kwargs={'sub_incoming': self._all_queue_urls()})
            proc.start()

            self._worker_procs.append(proc)

    def _next_worker(self) -> int:
        self._last_used_worker += 1

        if self._last_used_worker >= self.workers_count:
            self._last_used_worker = 0

        return self._last_used_worker

    async def _dispatch_connection(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        peer = w.get_extra_info('peername')
        worker_index = self._next_worker()
        logger.info("Incoming connection from {}, forwarding to worker #{}".format(
            peer, worker_index))

        sock = self._sock_for_worker(worker_index)
        worker_r, worker_w = await asyncio.open_unix_connection(sock, loop=self.loop)

        async def recv_forwarding():
            while True:
                buf = await r.read(self.BUFFER_SIZE)

                if len(buf) == 0:
                    logger.warning("Client {} closed connection".format(peer))
                    worker_w.close()
                    break

                logger.debug("Received {} bytes from {}, forwarding to worker #{}".format(
                    len(buf), peer, worker_index))

                worker_w.write(buf)
                await worker_w.drain()

        async def send_forwarding():
            while True:
                buf = await worker_r.read(self.BUFFER_SIZE)

                if len(buf) == 0:
                    logger.warning("Worker closed connection with {}".format(peer))
                    w.close()
                    break

                logger.debug("Received {} bytes from worker #{}, forwarding to {}".format(
                    len(buf), worker_index, peer))
                w.write(buf)
                await w.drain()

        await asyncio.gather(
            recv_forwarding(), send_forwarding(),
            loop=self.loop, return_exceptions=True)

    def run(self):
        logger.info("Starting master server at {}:{}".format(self.host, self.port))

        self._run_worker_procs()

        self.loop = asyncio.new_event_loop()

        server_gen = asyncio.start_server(
            self._dispatch_connection, self.host, self.port, loop=self.loop)
        self.aserver = self.loop.run_until_complete(server_gen)

        try:
            self.loop.run_until_complete(self.aserver.wait_closed())
        except asyncio.CancelledError:
            logger.info('Event loop has been cancelled')

        self.loop.close()

    def terminate(self):
        for p in self._worker_procs:
            p.terminate()

        async def _stop_cb():
            self.aserver.close()
            for task in asyncio.Task.all_tasks(loop=self.loop):
                task.cancel()

        self.loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(_stop_cb(), loop=self.loop))
