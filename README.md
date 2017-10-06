# SMPP Gateway Framework

This framework acts as a parsing and dispatching layer between the client
and the gateway logic (written by you).

You have to create a class, which implements the `Provider` interface found in
`external/base.py` source. This class will act as a backend for clients
authentification and message delivery. Specify your class in the configuration,
run the project and voila!

Currently it only supports sending messages but not receiving. The server can be
scaled into multiple worker processes. Each worker performs in asyncronous mode
using Python's asyncio module.

## Configuration

For configuration check out the heavily-commented `config.py` file.

## Testing

Run `test.py` to perform unit tests for `smpp.parse` module (located at
`smpp/parse_tests.py`) and functional tests for the whole projects
(`smpp/functests.py`).

These three scripts are now required to run the software and may be safely removed.

## Launching

### Via Docker (recommended)

1. Build the image by running `docker build -t smppserver`.
2. Run the container with
  `docker run -p 2775:2775 --restart always --name smppserver smppserver`
3. Stop the container with `docker stop smppserver`.

### Manually

1. This project requires Python version 3.5 or newer.
2. You should install zeromq library's development files into the system.
  On ubuntu distributions it can be found in the `libzmq-dev` package.
3. Install project dependencies: `pip install -r requirements.txt`.
4. Launch by running `main.py` script.
5. Stop by sending an interruption signal (e.g. with Ctrl+C).
