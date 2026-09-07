"""dashboard oauth2 and tenant rbac"""
from alembic import op

revision = "0008_dashboard_auth"
down_revision = "0007_promotions_loyalty"


def upgrade() -> None:
    op.execute("""
    CREATE TABLE tenants (
      id UUID PRIMARY KEY, discord_guild_id BIGINT NOT NULL UNIQUE,
      name VARCHAR(200) NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE dashboard_users (
      id UUID PRIMARY KEY, discord_user_id BIGINT NOT NULL UNIQUE, username VARCHAR(120) NOT NULL,
      global_name VARCHAR(120), avatar_hash VARCHAR(128), active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE tenant_memberships (
      id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
      user_id UUID NOT NULL REFERENCES dashboard_users(id) ON DELETE CASCADE,
      role VARCHAR(16) NOT NULL CHECK (role IN ('OWNER','ADMIN','OPERATOR','VIEWER')),
      active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (tenant_id, user_id)
    );
    CREATE TABLE oauth_states (
      id UUID PRIMARY KEY, state_hash VARCHAR(64) NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL,
      consumed_at TIMESTAMPTZ
    );
    CREATE INDEX ix_oauth_states_expires ON oauth_states(expires_at);
    CREATE TABLE dashboard_sessions (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES dashboard_users(id) ON DELETE CASCADE,
      tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
      token_hash VARCHAR(64) NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL,
      last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ
    );
    CREATE INDEX ix_dashboard_sessions_user ON dashboard_sessions(user_id);
    CREATE INDEX ix_dashboard_sessions_expires ON dashboard_sessions(expires_at);
    CREATE TABLE audit_logs (
      id UUID PRIMARY KEY, user_id UUID REFERENCES dashboard_users(id) ON DELETE SET NULL,
      tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL, action VARCHAR(120) NOT NULL,
      resource_type VARCHAR(64), resource_id VARCHAR(128), ip_address VARCHAR(64),
      metadata_json TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_audit_logs_created ON audit_logs(created_at);
    INSERT INTO tenants (id, discord_guild_id, name)
      VALUES ('00000000-0000-0000-0000-000000000001', 0, 'Default Tenant')
      ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs, dashboard_sessions, oauth_states, tenant_memberships, dashboard_users, tenants CASCADE")
