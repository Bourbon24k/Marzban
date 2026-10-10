"""Add Xray Hysteria2 accounts; SQLite enum storage already accepts new values."""
from alembic import op
import sqlalchemy as sa

revision = "yuku0014hy2"
down_revision = "yuku0013order"
branch_labels = None
depends_on = None

def upgrade():
    if op.get_bind().dialect.name == "sqlite":
        op.execute("CREATE UNIQUE INDEX uq_hysteria_auth ON proxies(json_extract(settings, '$.auth')) WHERE type = 'Hysteria'")
    if op.get_bind().dialect.name == "mysql":
        op.execute("ALTER TABLE proxies MODIFY type ENUM('VMess','VLESS','Trojan','Shadowsocks','Hysteria') NOT NULL")

def downgrade():
    count = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM proxies WHERE type = 'Hysteria'")).scalar()
    if count:
        raise RuntimeError("Remove Hysteria proxies before downgrading")
    if op.get_bind().dialect.name == "sqlite":
        op.drop_index("uq_hysteria_auth", table_name="proxies")
    if op.get_bind().dialect.name == "mysql":
        op.execute("ALTER TABLE proxies MODIFY type ENUM('VMess','VLESS','Trojan','Shadowsocks') NOT NULL")
