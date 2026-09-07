'use client';

import { useEffect, useMemo, useState } from 'react';

type Tenant = { id: string; guild_id: number; name: string; role: string };
type Me = { username: string; global_name?: string | null; tenants: Tenant[] };
type Overview = { role: string; orders: number; revenue_minor: number; active_products: number };
type Order = { id: string; discord_user_id: number; status: string; currency: string; total_minor: number; created_at: string };

async function api<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: 'include', cache: 'no-store' });
  if (!response.ok) throw new Error(`${response.status}`);
  return response.json();
}

const money = (minor: number, currency = 'BRL') => new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(minor / 100);

export default function Dashboard() {
  const [me, setMe] = useState<Me | null>(null);
  const [tenantId, setTenantId] = useState('');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api<Me>('/api/v1/auth/discord/me').then((value) => {
      setMe(value);
      setTenantId(value.tenants[0]?.id ?? '');
    }).catch(() => setError('Faça login com Discord para acessar o painel.'));
  }, []);

  useEffect(() => {
    if (!tenantId) return;
    Promise.all([
      api<Overview>(`/api/v1/dashboard/${tenantId}/overview`),
      api<Order[]>(`/api/v1/dashboard/${tenantId}/orders`),
    ]).then(([summary, orderRows]) => {
      setOverview(summary);
      setOrders(orderRows);
      setError('');
    }).catch(() => setError('Não foi possível carregar os dados deste servidor.'));
  }, [tenantId]);

  const tenant = useMemo(() => me?.tenants.find((item) => item.id === tenantId), [me, tenantId]);

  if (!me) {
    return (
      <main className="shell center">
        <section className="login-card">
          <span className="eyebrow">DISCORD COMMERCE PLATFORM</span>
          <h1>Painel de vendas</h1>
          <p>Entre com sua conta Discord para administrar lojas autorizadas.</p>
          {error && <div className="alert">{error}</div>}
          <a className="button primary" href="/api/v1/auth/discord/login">Entrar com Discord</a>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">DC<span>•</span>Commerce</div>
        <div className="muted">Conta</div>
        <strong>{me.global_name || me.username}</strong>
        <nav>
          <a className="active">Visão geral</a><a>Pedidos</a><a>Produtos</a><a>Clientes</a><a>Cupons & VIP</a><a>Pagamentos</a><a>Configurações</a>
        </nav>
      </aside>
      <section className="content">
        <header className="topbar">
          <div><span className="eyebrow">DASHBOARD</span><h1>{tenant?.name || 'Selecione uma loja'}</h1></div>
          <div className="toolbar">
            <select value={tenantId} onChange={(event) => setTenantId(event.target.value)}>{me.tenants.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.role}</option>)}</select>
            <button className="button" onClick={() => fetch('/api/v1/auth/discord/logout', { method: 'POST', credentials: 'include' }).then(() => location.reload())}>Sair</button>
          </div>
        </header>
        {error && <div className="alert">{error}</div>}
        <section className="grid">
          <article className="card"><span>Faturamento</span><strong>{money(overview?.revenue_minor ?? 0)}</strong><small>Pedidos pagos</small></article>
          <article className="card"><span>Pedidos</span><strong>{overview?.orders ?? 0}</strong><small>Todos os estados</small></article>
          <article className="card"><span>Produtos ativos</span><strong>{overview?.active_products ?? 0}</strong><small>Catálogo disponível</small></article>
          <article className="card"><span>Permissão</span><strong>{overview?.role ?? tenant?.role ?? 'VIEWER'}</strong><small>RBAC atual</small></article>
        </section>
        <section className="panel">
          <div className="panel-head"><div><span className="eyebrow">OPERAÇÃO</span><h2>Pedidos recentes</h2></div><span className="badge">{orders.length} registros</span></div>
          <div className="table-wrap"><table><thead><tr><th>Pedido</th><th>Cliente</th><th>Status</th><th>Total</th><th>Data</th></tr></thead><tbody>
            {orders.slice(0, 12).map((order) => <tr key={order.id}><td>#{order.id.slice(0, 8)}</td><td>{order.discord_user_id}</td><td><span className={`status ${order.status.toLowerCase()}`}>{order.status}</span></td><td>{money(order.total_minor, order.currency)}</td><td>{new Date(order.created_at).toLocaleString('pt-BR')}</td></tr>)}
            {!orders.length && <tr><td colSpan={5} className="empty">Nenhum pedido encontrado.</td></tr>}
          </tbody></table></div>
        </section>
      </section>
    </main>
  );
}
