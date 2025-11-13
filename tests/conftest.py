import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _install_clickhouse_stub() -> None:
    if "clickhouse_connect" in sys.modules:
        return

    class _FakeClient:
        def __getattr__(self, item):
            raise RuntimeError(f"ClickHouse stub missing attr {item!r}")

    def _get_client(*args, **kwargs):
        return _FakeClient()

    sys.modules["clickhouse_connect"] = types.SimpleNamespace(get_client=_get_client)


def _install_aiokafka_stub() -> None:
    if "aiokafka" in sys.modules:
        return

    class _DummyConsumer:
        def __init__(self, *args, **kwargs):
            self.started = False
            self.stopped = False

        async def start(self):
            self.started = True

        async def stop(self):
            self.stopped = True

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    sys.modules["aiokafka"] = types.SimpleNamespace(AIOKafkaConsumer=_DummyConsumer)


_install_clickhouse_stub()
_install_aiokafka_stub()
