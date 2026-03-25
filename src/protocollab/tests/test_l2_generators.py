import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Generator

import pytest

from protocollab.generators.l2_client import L2ClientGenerator
from protocollab.generators.l2_server import L2ServerGenerator
from protocollab.generators.python_generator import PythonGenerator
from protocollab.loader import load_protocol

GENERATED_MODULE_NAMES = (
    "ping_protocol_parser",
    "ping_protocol_l2_client",
    "ping_protocol_l2_server",
)
SCAPY_MODULE_NAMES = ("scapy", "scapy.all")


def _clear_generated_modules() -> None:
    for module_name in GENERATED_MODULE_NAMES + SCAPY_MODULE_NAMES:
        sys.modules.pop(module_name, None)
    importlib.invalidate_caches()


def _install_fake_scapy(monkeypatch: pytest.MonkeyPatch):
    sent_packets = []
    srp1_calls = []

    class FakeRaw:
        def __init__(self, load):
            self.load = load

    class FakeEther:
        def __init__(self, src=None, dst=None, type=None):
            self.src = src
            self.dst = dst
            self.type = type
            self.raw = None

        def __truediv__(self, other):
            self.raw = other
            return self

        def getlayer(self, layer):
            if layer is FakeEther:
                return self
            if layer is FakeRaw:
                return self.raw
            return None

    class FakeThread:
        def __init__(self):
            self._alive = False

        def join(self, timeout=None):
            return None

        def is_alive(self):
            return self._alive

    class FakeAsyncSniffer:
        def __init__(self, iface, store, prn, lfilter):
            self.iface = iface
            self.store = store
            self.prn = prn
            self.lfilter = lfilter
            self.thread = FakeThread()

        def start(self):
            self.thread._alive = True

        def stop(self, join=False):
            self.thread._alive = False
            return []

    def fake_sendp(packet, iface, verbose=False):
        sent_packets.append((packet, iface, verbose))

    def fake_srp1(packet, iface, timeout, verbose=False):
        srp1_calls.append((packet, iface, timeout, verbose))
        return FakeEther(src=packet.dst, dst=packet.src, type=packet.type) / FakeRaw(
            packet.raw.load
        )

    fake_all = ModuleType("scapy.all")
    fake_all.Ether = FakeEther
    fake_all.Raw = FakeRaw
    fake_all.sendp = fake_sendp
    fake_all.srp1 = fake_srp1
    fake_all.AsyncSniffer = FakeAsyncSniffer

    fake_scapy = ModuleType("scapy")
    fake_scapy.all = fake_all

    monkeypatch.setitem(sys.modules, "scapy", fake_scapy)
    monkeypatch.setitem(sys.modules, "scapy.all", fake_all)

    return SimpleNamespace(
        Ether=FakeEther,
        Raw=FakeRaw,
        sent_packets=sent_packets,
        srp1_calls=srp1_calls,
    )


def _import_generated_module(module_dir: Path, module_name: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(module_dir))
    return importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def clear_generated_module_cache() -> Generator[None, None, None]:
    _clear_generated_modules()
    yield
    _clear_generated_modules()


@pytest.fixture
def ping_spec():
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    file_path = project_root / "examples" / "simple" / "ping_protocol.yaml"
    if not file_path.exists():
        pytest.skip(f"Spec file not found: {file_path}")
    return load_protocol(str(file_path))


def generate_l2_files(spec, output_dir, generator_class):
    generator = generator_class()
    return generator.generate(spec, output_dir)


def test_l2_client_generation(ping_spec, tmp_path, monkeypatch):
    PythonGenerator().generate(ping_spec, tmp_path)
    fake_scapy = _install_fake_scapy(monkeypatch)

    output_files = generate_l2_files(ping_spec, tmp_path, L2ClientGenerator)
    assert len(output_files) == 1
    assert output_files[0].name == "ping_protocol_l2_client.py"

    module = _import_generated_module(tmp_path, "ping_protocol_l2_client", monkeypatch)
    client = module.L2ScapyClient("eth0", "02:00:00:00:00:01", "02:00:00:00:00:02")
    parser = _import_generated_module(tmp_path, "ping_protocol_parser", monkeypatch).PingProtocol

    response = client.send_and_receive(parser(type_id=0, sequence_number=7, payload_size=8))

    assert response.sequence_number == 7
    assert fake_scapy.srp1_calls[0][1] == "eth0"


def test_l2_client_receive_is_not_supported(ping_spec, tmp_path, monkeypatch):
    PythonGenerator().generate(ping_spec, tmp_path)
    _install_fake_scapy(monkeypatch)
    generate_l2_files(ping_spec, tmp_path, L2ClientGenerator)

    l2_client = _import_generated_module(
        tmp_path, "ping_protocol_l2_client", monkeypatch
    ).L2ScapyClient
    client = l2_client("eth0", "02:00:00:00:00:01", "02:00:00:00:00:02")

    with pytest.raises(NotImplementedError, match="send_and_receive"):
        client.receive()


def test_l2_server_generation_and_stop(ping_spec, tmp_path, monkeypatch):
    PythonGenerator().generate(ping_spec, tmp_path)
    fake_scapy = _install_fake_scapy(monkeypatch)

    output_files = generate_l2_files(ping_spec, tmp_path, L2ServerGenerator)
    assert len(output_files) == 1
    assert output_files[0].name == "ping_protocol_l2_server.py"

    parser = _import_generated_module(tmp_path, "ping_protocol_parser", monkeypatch).PingProtocol
    module = _import_generated_module(tmp_path, "ping_protocol_l2_server", monkeypatch)
    server = module.L2ScapyServer("eth0", "02:00:00:00:00:02")

    server.start()
    assert server.is_alive()

    request = fake_scapy.Ether(
        src="02:00:00:00:00:01",
        dst="02:00:00:00:00:02",
        type=0x88B5,
    ) / fake_scapy.Raw(parser(type_id=0, sequence_number=5, payload_size=8).serialize())
    server._handle_packet(request)

    assert fake_scapy.sent_packets
    server.stop(timeout=0.1)
    assert not server.is_alive()
