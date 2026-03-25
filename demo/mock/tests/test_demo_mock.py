import importlib
import sys
import queue
from pathlib import Path

DEMO_MOCK_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = DEMO_MOCK_DIR / "generated"
sys.path.insert(0, str(DEMO_MOCK_DIR))
sys.path.insert(0, str(GENERATED_DIR))


def _generate_demo_files() -> None:
    demo_cli = importlib.import_module("demo")
    demo_cli.generate_demo_files()


def setup_module():
    _generate_demo_files()


def test_imports():
    """Проверяем, что все сгенерированные модули импортируются."""
    from ping_protocol_parser import PingProtocol
    from ping_protocol_mock_client import MockClient
    from ping_protocol_mock_server import MockServer

    assert callable(PingProtocol.parse)
    assert callable(MockClient.send)
    assert callable(MockServer.start)


def test_ping_protocol_serialize_deserialize():
    from ping_protocol_parser import PingProtocol

    original = PingProtocol(type_id=0, sequence_number=123, payload_size=8)
    data = original.serialize()
    parsed = PingProtocol.parse(data)

    assert parsed.type_id == original.type_id
    assert parsed.sequence_number == original.sequence_number
    assert parsed.payload_size == original.payload_size


def test_mock_client_server_interaction():
    from ping_protocol_parser import PingProtocol
    from ping_protocol_mock_client import MockClient
    from ping_protocol_mock_server import MockServer

    client_to_server = queue.Queue()
    server_to_client = queue.Queue()

    def ping_handler(request):
        if request.type_id == 0:
            return PingProtocol(
                type_id=1,
                sequence_number=request.sequence_number,
                payload_size=request.payload_size,
            )
        return request

    server = MockServer(client_to_server, server_to_client, handler=ping_handler)
    server.start()

    client = MockClient(client_to_server, server_to_client)

    ping = PingProtocol(type_id=0, sequence_number=42, payload_size=16)
    response = client.send_and_receive(ping, timeout=2.0)

    assert response is not None
    assert response.type_id == 1
    assert response.sequence_number == 42
    assert response.payload_size == 16

    server.stop()


def test_mock_client_timeout():
    from ping_protocol_parser import PingProtocol
    from ping_protocol_mock_client import MockClient

    client_to_server = queue.Queue()
    server_to_client = queue.Queue()
    client = MockClient(client_to_server, server_to_client)

    ping = PingProtocol(type_id=0, sequence_number=1, payload_size=8)
    client.send(ping)
    response = client.receive(timeout=0.5)

    assert response is None


def test_mock_server_default_handler():
    from ping_protocol_parser import PingProtocol
    from ping_protocol_mock_client import MockClient
    from ping_protocol_mock_server import MockServer

    client_to_server = queue.Queue()
    server_to_client = queue.Queue()
    server = MockServer(client_to_server, server_to_client)  # no handler -> echo
    server.start()

    client = MockClient(client_to_server, server_to_client)

    ping = PingProtocol(type_id=0, sequence_number=42, payload_size=8)
    response = client.send_and_receive(ping, timeout=2.0)

    assert response is not None
    assert response.type_id == 0
    assert response.sequence_number == 42
    assert response.payload_size == 8

    server.stop()
