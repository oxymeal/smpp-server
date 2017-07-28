#!/usr/bin/env python3
import config
import logging
from smpp.master import MasterServer

logger = logging.getLogger(__name__)

def main():
    master = MasterServer(
        host=config.HOST,
        port=config.PORT,
        provider=config.EXTERNAL_PROVIDER,
        workers_count=config.WORKERS_COUNT,
        worker_socket_template=config.WORKER_SOCKET_TEMPLATE,
        incoming_queue_base_port=config.INCOMING_MESSAGES_QUEUE_BASE_PORT)

    try:
        master.run()
    except KeyboardInterrupt:
        logger.info("Shutting down master server...")
        master.terminate()
        logger.info("Shut down.")

if __name__ == '__main__':
    main()
