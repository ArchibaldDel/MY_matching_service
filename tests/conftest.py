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
        def command(self, *args, **kwargs):
            return None

        def query(self, *args, **kwargs):
            class _Result:
                result_rows = []
            return _Result()

        def insert(self, *args, **kwargs):
            return None

    def _get_client(*args, **kwargs):
        return _FakeClient()

    module = types.SimpleNamespace(get_client=_get_client)
    sys.modules["clickhouse_connect"] = module


def _install_kafka_stub() -> None:
    if "confluent_kafka" in sys.modules:
        return

    class _Producer:
        def __init__(self, *_, **__):
            self.messages = []

        def produce(self, topic, key, value, on_delivery):
            self.messages.append((topic, key, value))
            on_delivery(None, types.SimpleNamespace(topic=lambda: topic, partition=lambda: 0))

        def poll(self, timeout):
            pass

        def flush(self):
            pass

    module = types.SimpleNamespace(Producer=_Producer)
    sys.modules["confluent_kafka"] = module


_install_clickhouse_stub()
_install_kafka_stub()
