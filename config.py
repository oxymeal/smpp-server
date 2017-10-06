# Host and port for the server to listen on
HOST = '0.0.0.0'
PORT = 2775

# Number of workers (dedicated system processes, processing incoming SMPP requests)
WORKERS_COUNT = 2

# Gateway backend section
import smpp.external.logging

# This function should build a new Provider given the server.
def build_provider(server, **kwargs):
    # If you require access to the server's event loop, store the server
    # object in you Provider instance, then access the loop via server.loop
    # attribute.
    return smpp.external.logging.Provider(file_path="container/sms.txt")

PROVIDER_BUILDER = build_provider

# Logging options
import logging
logging.basicConfig(level=logging.DEBUG)

# Template for worker's unix socket path
WORKER_SOCKET_TEMPLATE = '/tmp/smpp_server_{port}_worker_{i}.sock'
# Each worker allocates a unix socket, which are used by master process
# to forward incoming traffic to the workers.

# Initial port for incoming queue server
INCOMING_MESSAGES_QUEUE_BASE_PORT = 25555
# Each worker starts a queue server, which is used to distribute delivery
# receipts among all the workers to send to all the client's connections.
# First worker will bind to the initial queue port (e.g. 25555). The second worker
# will bind to the next port (25556) and so on.
