"""promotions and loyalty tables"""

from alembic import op

revision = "0007_promotions_loyalty"
down_revision = "0006_fulfillment"


def upgrade() -> None:
    op.execute("""
    CREATE TABLE coupons (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, code VARCHAR(64) NOT NULL, discount_type VARCHAR(16) NOT NULL CHECK (discount_type IN ('PERCENT','FIXED')), discount_value BIGINT NOT NULL CHECK (discount_value > 0), currency VARCHAR(3), min_order_minor BIGINT NOT NULL DEFAULT 0 CHECK (min_order_minor >= 0), max_discount_minor BIGINT CHECK (max_discount_minor IS NULL OR max_discount_minor >= 0), usage_limit INTEGER CHECK (usage_limit IS NULL OR usage_limit > 0), per_user_limit INTEGER NOT NULL DEFAULT 1 CHECK (per_user_limit > 0), used_count INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0), starts_at TIMESTAMPTZ, ends_at TIMESTAMPTZ, active BOOLEAN NOT NULL DEFAULT TRUE, UNIQUE (tenant_id, code));
    CREATE INDEX ix_coupons_tenant_active ON coupons(tenant_id, active);
    CREATE TABLE coupon_usages (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, coupon_id UUID NOT NULL REFERENCES coupons(id), discord_user_id BIGINT NOT NULL, order_id UUID NOT NULL, discount_minor BIGINT NOT NULL CHECK (discount_minor >= 0), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (coupon_id, order_id));
    CREATE INDEX ix_coupon_usages_user ON coupon_usages(tenant_id, discord_user_id, coupon_id);
    CREATE TABLE order_promotions (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, order_id UUID NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE, coupon_id UUID REFERENCES coupons(id), coupon_code VARCHAR(64), discount_minor BIGINT NOT NULL DEFAULT 0, affiliate_id UUID, affiliate_code VARCHAR(64), cashback_bps INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE cashback_wallets (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, discord_user_id BIGINT NOT NULL, balance_minor BIGINT NOT NULL DEFAULT 0 CHECK (balance_minor >= 0), currency VARCHAR(3) NOT NULL DEFAULT 'BRL', updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (tenant_id, discord_user_id));
    CREATE TABLE cashback_ledger (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, discord_user_id BIGINT NOT NULL, order_id UUID, type VARCHAR(24) NOT NULL CHECK (type IN ('EARN','REDEEM','ADJUSTMENT')), amount_minor BIGINT NOT NULL CHECK (amount_minor > 0), idempotency_key VARCHAR(160) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (tenant_id, idempotency_key));
    CREATE TABLE affiliates (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, discord_user_id BIGINT NOT NULL, code VARCHAR(64) NOT NULL, commission_bps INTEGER NOT NULL DEFAULT 500 CHECK (commission_bps BETWEEN 0 AND 10000), active BOOLEAN NOT NULL DEFAULT TRUE, UNIQUE (tenant_id, code), UNIQUE (tenant_id, discord_user_id));
    CREATE TABLE affiliate_attributions (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, affiliate_id UUID NOT NULL REFERENCES affiliates(id), order_id UUID NOT NULL, commission_minor BIGINT NOT NULL CHECK (commission_minor >= 0), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (tenant_id, order_id));
    CREATE TABLE vip_tiers (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, name VARCHAR(64) NOT NULL, min_spend_minor BIGINT NOT NULL CHECK (min_spend_minor >= 0), discount_bps INTEGER NOT NULL DEFAULT 0 CHECK (discount_bps BETWEEN 0 AND 10000), cashback_bps INTEGER NOT NULL DEFAULT 0 CHECK (cashback_bps BETWEEN 0 AND 10000), UNIQUE (tenant_id, name));
    CREATE TABLE vip_memberships (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, discord_user_id BIGINT NOT NULL, tier_id UUID NOT NULL REFERENCES vip_tiers(id), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (tenant_id, discord_user_id));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vip_memberships, vip_tiers, affiliate_attributions, affiliates, cashback_ledger, cashback_wallets, order_promotions, coupon_usages, coupons CASCADE")
