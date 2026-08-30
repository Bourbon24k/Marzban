import importlib.util
import sys
import threading
import types
import unittest
from enum import Enum
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


class NodeStatus(str, Enum):
    connected = "connected"
    connecting = "connecting"
    error = "error"
    disabled = "disabled"


class DummyApp:
    def on_event(self, _name):
        return lambda func: func


class FakeDB:
    def rollback(self):
        pass


class FakeDBContext:
    def __enter__(self):
        return FakeDB()

    def __exit__(self, *_args):
        pass


class FakeCrud:
    def __init__(self, dbnode, block_first_lookup=False):
        self.dbnode = dbnode
        self.statuses = []
        self.lookup_calls = 0
        self.lookups_before_release = 0
        self.first_lookup_entered = threading.Event()
        self.release_first_lookup = threading.Event()
        self.block_first_lookup = block_first_lookup

    def get_node_by_id(self, _db, _node_id):
        self.lookup_calls += 1
        if self.block_first_lookup and not self.release_first_lookup.is_set():
            self.lookups_before_release += 1
        if self.block_first_lookup and self.lookup_calls == 1:
            self.first_lookup_entered.set()
            self.release_first_lookup.wait(timeout=2)
        return self.dbnode

    def update_node_status(self, _db, dbnode, status, message=None, version=None):
        dbnode.status = status
        dbnode.message = message
        dbnode.xray_version = version
        self.statuses.append((status, message, version))


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def load_operations(dbnode, node, *, block_first_lookup=False):
    crud = FakeCrud(dbnode, block_first_lookup=block_first_lookup)
    xray = types.SimpleNamespace(
        nodes={dbnode.id: node},
        config=types.SimpleNamespace(include_db_users=lambda: {"inbounds": []}),
        exc=types.SimpleNamespace(ConnectionError=Exception),
    )

    _install_module("app", logger=Mock(), xray=xray)
    _install_module("app.db", GetDB=FakeDBContext, crud=crud)
    _install_module("app.models")
    _install_module("app.models.node", NodeStatus=NodeStatus)
    _install_module("app.models.user", UserResponse=object)
    _install_module("app.utils")
    _install_module("app.utils.concurrency", threaded_function=lambda func: func)
    _install_module("app.xray")
    _install_module("app.xray.node", XRayNode=object)
    _install_module("sqlalchemy")
    _install_module("sqlalchemy.exc", SQLAlchemyError=Exception)

    class Account:
        pass

    class XTLSFlows:
        NONE = "none"

    _install_module("xray_api", XRay=object)
    _install_module("xray_api.types")
    _install_module("xray_api.types.account", Account=Account, XTLSFlows=XTLSFlows)

    spec = importlib.util.spec_from_file_location(
        "operations_under_test", ROOT / "app/xray/operations.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    xray.operations = module
    return module, crud


def load_health_job(node):
    class XrayError(Exception):
        pass

    operations = types.SimpleNamespace(restart_node=Mock(), connect_node=Mock())
    xray = types.SimpleNamespace(
        core=types.SimpleNamespace(started=True),
        nodes={7: node},
        operations=operations,
        config=types.SimpleNamespace(include_db_users=lambda: {"inbounds": []}),
    )
    _install_module(
        "app",
        app=DummyApp(),
        logger=Mock(),
        scheduler=Mock(),
        xray=xray,
    )
    _install_module("app.db", GetDB=FakeDBContext, crud=Mock())
    _install_module("app.models")
    _install_module("app.models.node", NodeStatus=NodeStatus)
    _install_module("config", JOB_CORE_HEALTH_CHECK_INTERVAL=60)
    _install_module("xray_api")
    _install_module("xray_api.exc", XrayError=XrayError)

    spec = importlib.util.spec_from_file_location(
        "health_job_under_test", ROOT / "app/jobs/0_xray_core.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, operations, XrayError


def load_node_module():
    class HTTPAdapter:
        pass

    class Service:
        pass

    _install_module("grpc", FutureTimeoutError=TimeoutError)
    _install_module("requests", Session=object)
    _install_module("requests.adapters", HTTPAdapter=HTTPAdapter)
    _install_module("requests.packages")
    _install_module("requests.packages.urllib3")
    _install_module(
        "requests.packages.urllib3.poolmanager",
        PoolManager=object,
    )
    _install_module("rpyc", Service=Service, BgServingThread=object)
    _install_module(
        "websocket",
        WebSocketConnectionClosedException=Exception,
        WebSocketTimeoutException=TimeoutError,
        create_connection=Mock(),
    )
    _install_module("app")
    _install_module("app.xray")
    _install_module("app.xray.config", XRayConfig=object)
    _install_module("xray_api", XRay=object)

    spec = importlib.util.spec_from_file_location(
        "node_under_test", ROOT / "app/xray/node.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeNode:
    def __init__(self, *, restart_error=None):
        self.connected = True
        self.started = True
        self.restart_error = restart_error
        self.restart_calls = 0
        self.start_calls = 0

    def start(self, _config):
        self.start_calls += 1

    def restart(self, _config):
        self.restart_calls += 1
        if self.restart_error:
            raise self.restart_error

    def get_version(self):
        return "26.6.1"

    def disconnect(self):
        self.connected = False


class NodeRecoveryTests(unittest.TestCase):
    def test_duplicate_connect_is_rejected_before_database_or_network_work(self):
        """Removing the per-node gate must let both lookups enter concurrently."""
        dbnode = types.SimpleNamespace(
            id=7,
            name="node",
            status=NodeStatus.connected,
            message=None,
            xray_version="26.6.1",
        )
        node = FakeNode()
        operations, crud = load_operations(dbnode, node, block_first_lookup=True)

        first = threading.Thread(target=operations.connect_node, args=(7, {}))
        second = threading.Thread(target=operations.connect_node, args=(7, {}))
        first.start()
        self.assertTrue(crud.first_lookup_entered.wait(timeout=1))
        second.start()
        second.join(timeout=0.2)
        crud.release_first_lookup.set()
        first.join(timeout=2)
        second.join(timeout=2)

        self.assertEqual(crud.lookups_before_release, 1)
        self.assertEqual(node.start_calls, 1)

    def test_successful_restart_restores_connected_status(self):
        """Removing the status update must leave a recovered node marked error."""
        dbnode = types.SimpleNamespace(
            id=7,
            name="node",
            status=NodeStatus.error,
            message="old timeout",
            xray_version="26.6.1",
        )
        node = FakeNode()
        operations, crud = load_operations(dbnode, node)

        operations.restart_node(7, {})

        self.assertEqual(node.restart_calls, 1)
        self.assertTrue(crud.statuses)
        self.assertEqual(crud.statuses[-1], (NodeStatus.connected, None, "26.6.1"))

    def test_failed_restart_reconnects_immediately(self):
        """Removing the fallback must leave Xray down until the next health cycle."""
        dbnode = types.SimpleNamespace(
            id=7,
            name="legacy node",
            status=NodeStatus.connected,
            message=None,
            xray_version="26.3.27",
        )
        broken = FakeNode(restart_error=RuntimeError("connection.peer is None"))
        replacement = FakeNode()
        operations, crud = load_operations(dbnode, broken)

        def replace_node(_dbnode):
            operations.xray.nodes[7] = replacement
            return replacement

        operations.add_node = replace_node

        operations.restart_node(7, {})

        self.assertEqual(replacement.start_calls, 1)
        self.assertEqual(crud.statuses[-1], (NodeStatus.connected, None, "26.6.1"))

    def test_health_check_requires_three_consecutive_failures(self):
        """Changing the threshold to one must restart after a transient miss."""
        node = types.SimpleNamespace(connected=True, started=True)
        job, operations, XrayError = load_health_job(node)
        failing_api = Mock()
        failing_api.get_sys_stats.side_effect = XrayError("temporary timeout")
        node.api = failing_api

        job.core_health_check()
        job.core_health_check()
        self.assertEqual(operations.restart_node.call_count, 0)

        job.core_health_check()
        self.assertEqual(operations.restart_node.call_count, 1)

    def test_successful_health_check_resets_failure_streak(self):
        """Removing the reset must combine non-consecutive misses into a restart."""
        node = types.SimpleNamespace(connected=True, started=True)
        job, operations, XrayError = load_health_job(node)
        api = Mock()
        node.api = api
        api.get_sys_stats.side_effect = [
            XrayError("miss 1"),
            XrayError("miss 2"),
            None,
            XrayError("miss 1 again"),
            XrayError("miss 2 again"),
        ]

        for _ in range(5):
            job.core_health_check()

        self.assertEqual(operations.restart_node.call_count, 0)

    def test_disconnected_node_requires_three_consecutive_failures(self):
        """Immediate reconnect on one failed ping must not flap a live node."""
        node = types.SimpleNamespace(connected=False, started=True, api=Mock())
        job, operations, _ = load_health_job(node)

        job.core_health_check()
        job.core_health_check()
        self.assertEqual(operations.connect_node.call_count, 0)

        job.core_health_check()
        self.assertEqual(operations.connect_node.call_count, 1)

    def test_rpyc_ping_timeout_does_not_destroy_the_connection(self):
        """A transient slow ping must remain eligible for the next health probe."""
        node_module = load_node_module()
        connection = types.SimpleNamespace(
            ping=Mock(side_effect=TimeoutError("result expired")),
            close=Mock(),
            closed=False,
        )
        node = object.__new__(node_module.RPyCXRayNode)
        node.connection = connection

        self.assertFalse(node.connected)
        self.assertTrue(hasattr(node, "connection"))
        self.assertIs(node.connection, connection)
        connection.close.assert_not_called()

    def test_rpyc_connect_allows_slow_but_live_ping(self):
        """Restoring the three-second ping must reject a responsive distant node."""
        node_module = load_node_module()
        received = {}

        class SlowConnection:
            closed = False

            def ping(self, timeout=3):
                if timeout < 10:
                    raise TimeoutError("result expired")

            def close(self):
                self.closed = True

        connection = SlowConnection()

        def ssl_connect(*_args, **kwargs):
            received.update(kwargs)
            return connection

        node_module.rpyc.ssl_connect = ssl_connect
        node_module.ssl.get_server_certificate = lambda *_args, **_kwargs: "cert"
        node = node_module.RPyCXRayNode(
            address="192.0.2.1",
            port=62050,
            api_port=62051,
            ssl_key="key",
            ssl_cert="cert",
        )

        try:
            node.connect()
        except TimeoutError as exc:
            self.fail(f"slow live node was rejected: {exc}")

        self.assertIs(node.connection, connection)
        self.assertGreaterEqual(received["config"]["sync_request_timeout"], 120)

    def test_node_type_detection_allows_distant_rest_agent_latency(self):
        """A one-second probe must not misclassify a distant REST agent as RPyC."""
        node_module = load_node_module()
        observed = {}

        class FakeSocket:
            def __init__(self, *_args, **_kwargs):
                pass

            def settimeout(self, timeout):
                observed["timeout"] = timeout

            def connect(self, _address):
                pass

            def send(self, _request):
                pass

            def recv(self, _size):
                return b""

            def close(self):
                pass

        class RestMarker:
            def __init__(self, **_kwargs):
                pass

        class RpycMarker:
            def __init__(self, **_kwargs):
                pass

        node_module.socket.socket = FakeSocket
        node_module.ReSTXRayNode = RestMarker
        node_module.RPyCXRayNode = RpycMarker

        node = node_module.XRayNode("192.0.2.1", 62050, 62051, "key", "cert")

        self.assertIsInstance(node, RestMarker)
        self.assertGreaterEqual(observed["timeout"], 5)


if __name__ == "__main__":
    unittest.main()
