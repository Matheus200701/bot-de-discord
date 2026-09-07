CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS products (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  sku varchar(80) NOT NULL,
  name varchar(200) NOT NULL,
  description text,
  price_minor bigint NOT NULL CHECK (price_minor >= 0),
  currency char(3) NOT NULL,
  stock_quantity integer NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
  active boolean NOT NULL DEFAULT true,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, sku)
);

CREATE TABLE IF NOT EXISTS orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  discord_user_id bigint NOT NULL,
  status varchar(32) NOT NULL,
  currency char(3) NOT NULL,
  total_minor bigint NOT NULL CHECK (total_minor >= 0),
  idempotency_key varchar(128) NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payment_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider varchar(40) NOT NULL,
  provider_event_id varchar(200) NOT NULL UNIQUE,
  event_type varchar(100) NOT NULL,
  payload jsonb NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_products_tenant_active ON products (tenant_id, active);
CREATE INDEX IF NOT EXISTS ix_orders_tenant_user ON orders (tenant_id, discord_user_id);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status);
