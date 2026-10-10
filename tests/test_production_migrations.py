import importlib.util
import unittest
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
ROOT = Path(__file__).resolve().parents[1]


class ProductionMigrationTests(unittest.TestCase):
    def test_order_and_hysteria_index_upgrade_and_guarded_downgrade(self):
        engine = create_engine('sqlite:///:memory:')
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE hosts (id INTEGER PRIMARY KEY)'))
            conn.execute(text('INSERT INTO hosts(id) VALUES (9), (4)'))
            conn.execute(text('CREATE TABLE proxies (id INTEGER PRIMARY KEY, type TEXT, settings JSON)'))
            modules = []
            for name in ('yuku0013_host_position', 'yuku0014_hysteria'):
                spec = importlib.util.spec_from_file_location(name, ROOT / f'app/db/migrations/versions/{name}.py')
                mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
                mod.op = Operations(MigrationContext.configure(conn)); modules.append(mod); mod.upgrade()
            self.assertEqual(conn.execute(text('SELECT id, position FROM hosts ORDER BY position')).all(), [(4, 4), (9, 9)])
            conn.execute(text("INSERT INTO proxies VALUES (1, 'Hysteria', '{\"auth\":\"fixture\"}')"))
            with self.assertRaises(IntegrityError):
                with conn.begin_nested():
                    conn.execute(text("INSERT INTO proxies VALUES (2, 'Hysteria', '{\"auth\":\"fixture\"}')"))
            conn.execute(text("INSERT INTO proxies VALUES (3, 'VLESS', '{\"auth\":\"fixture\"}')"))
            with self.assertRaises(RuntimeError): modules[1].downgrade()
            conn.execute(text("DELETE FROM proxies WHERE type = 'Hysteria'"))
            modules[1].downgrade(); modules[0].downgrade()
            self.assertNotIn('position', [r[1] for r in conn.execute(text('PRAGMA table_info(hosts)'))])
        engine.dispose()


if __name__ == '__main__': unittest.main()
