export default function Dashboard() {
  const cards = [
    ["Revenue", "R$ 0,00"],
    ["Orders", "0"],
    ["Customers", "0"],
    ["Refund rate", "0%"],
  ];
  return (
    <main style={{ padding: 32, fontFamily: "system-ui" }}>
      <h1>Discord Commerce</h1>
      <p>Production dashboard foundation.</p>
      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
        {cards.map(([label, value]) => (
          <article key={label} style={{ border: "1px solid #ddd", borderRadius: 12, padding: 20 }}>
            <small>{label}</small><h2>{value}</h2>
          </article>
        ))}
      </section>
    </main>
  );
}
