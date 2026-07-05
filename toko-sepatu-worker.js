export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "GET" && path === "/api/products") {
      await initDB(env.DB);
      const products = await env.DB.prepare("SELECT * FROM products").all();
      return json(products.results);
    }

    if (request.method === "POST" && path === "/api/order") {
      await initDB(env.DB);
      const body = await request.json().catch(() => ({}));
      const { product_id, name, phone, address, quantity } = body;
      if (!product_id || !name || !phone || !address || !quantity) {
        return json({ error: "Data pesanan kurang lengkap" }, 400);
      }
      const product = await env.DB.prepare("SELECT * FROM products WHERE id = ?").bind(product_id).first();
      if (!product) return json({ error: "Produk tidak ditemukan" }, 404);
      const total = product.price * Number(quantity);
      const orderId = crypto.randomUUID();
      await env.DB.prepare(`
        INSERT INTO orders (id, product_id, customer_name, phone, address, quantity, total, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'))
      `).bind(orderId, product_id, name, phone, address, quantity, total).run();
      return json({ ok: true, order_id: orderId, total });
    }

    if (request.method === "POST" && path === "/api/chat") {
      await initDB(env.DB);
      const body = await request.json().catch(() => ({}));
      const { message } = body;
      if (!message) return json({ error: "Pesan kosong" }, 400);
      const products = await env.DB.prepare("SELECT id, name, brand, price FROM products").all();
      const productList = products.results.map(p => `- ${p.name} (${p.brand}) - Rp${p.price.toLocaleString('id-ID')}`).join("\n");
      const prompt = `Kamu adalah customer service AI Toko Sepatu Online. Bantu pelanggan dengan ramah, singkat, dan jelas.\n\nDaftar produk tersedia:\n${productList}\n\nPertanyaan pelanggan: ${message}\n\nJawaban:`;
      const response = await env.AI.run("@cf/moonshotai/kimi-k2.6", { messages: [{ role: "user", content: prompt }] });
      const reply = response.choices?.[0]?.message?.content || response.response || "";
      return json({ reply });
    }

    if (request.method === "GET" && path === "/api/init") {
      await initDB(env.DB);
      return json({ ok: true });
    }

    return new Response(html, { headers: { "Content-Type": "text/html" }, status: 200 });
  }
};

async function initDB(db) {
  await db.prepare(`
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      brand TEXT NOT NULL,
      price INTEGER NOT NULL,
      image TEXT,
      stock INTEGER DEFAULT 0
    )
  `).run();
  await db.prepare(`
    CREATE TABLE IF NOT EXISTS orders (
      id TEXT PRIMARY KEY,
      product_id INTEGER NOT NULL,
      customer_name TEXT NOT NULL,
      phone TEXT NOT NULL,
      address TEXT NOT NULL,
      quantity INTEGER NOT NULL,
      total INTEGER NOT NULL,
      status TEXT DEFAULT 'pending',
      created_at TEXT
    )
  `).run();
  const existing = await db.prepare("SELECT COUNT(*) as c FROM products").first();
  if (existing.c === 0) {
    await db.prepare("INSERT INTO products (name, brand, price, image, stock) VALUES (?, ?, ?, ?, ?)")
      .bind("AirMax Runner", "Nike", 1899000, "https://placehold.co/400x300?text=AirMax", 10).run();
    await db.prepare("INSERT INTO products (name, brand, price, image, stock) VALUES (?, ?, ?, ?, ?)")
      .bind("Ultra Boost 22", "Adidas", 2100000, "https://placehold.co/400x300?text=Ultraboost", 8).run();
    await db.prepare("INSERT INTO products (name, brand, price, image, stock) VALUES (?, ?, ?, ?, ?)")
      .bind("GT-2000 11", "Asics", 1650000, "https://placehold.co/400x300?text=GT-2000", 6).run();
    await db.prepare("INSERT INTO products (name, brand, price, image, stock) VALUES (?, ?, ?, ?, ?)")
      .bind("Sketcher GoWalk", "Skechers", 950000, "https://placehold.co/400x300?text=GoWalk", 15).run();
  }
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

const html = `<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Toko Sepatu Online</title>
<style>
:root { --primary:#2563eb; --bg:#f8fafc; --card:#fff; --text:#1e293b; }
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); line-height:1.5; }
header { background:var(--primary); color:#fff; padding:1.2rem 1rem; text-align:center; }
header h1 { font-size:1.6rem; }
main { max-width:960px; margin:0 auto; padding:1rem; }
.products { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:1rem; margin:1.5rem 0; }
.product { background:var(--card); border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,.08); transition:transform .15s; }
.product:hover { transform:translateY(-4px); }
.product img { width:100%; height:180px; object-fit:cover; }
.product .info { padding:1rem; }
.product h3 { font-size:1rem; margin-bottom:.25rem; }
.product .brand { color:#64748b; font-size:.85rem; }
.product .price { font-weight:700; color:var(--primary); margin:.5rem 0; }
.product button { width:100%; padding:.6rem; border:none; border-radius:8px; background:var(--primary); color:#fff; cursor:pointer; }
.modal, .chatbox { display:none; position:fixed; background:var(--card); border-radius:16px; box-shadow:0 10px 40px rgba(0,0,0,.2); overflow:hidden; }
.modal { top:50%; left:50%; transform:translate(-50%,-50%); width:min(90%,420px); }
.modal.active, .chatbox.active { display:block; }
.modal h2, .chat-head { background:var(--primary); color:#fff; padding:1rem; font-size:1rem; }
.modal form, .chat-body { padding:1rem; }
.modal label { display:block; font-size:.85rem; margin:.5rem 0 .25rem; }
.modal input, .modal textarea, .chat-body textarea { width:100%; padding:.6rem; border:1px solid #cbd5e1; border-radius:8px; font:inherit; }
.modal .actions, .chat-actions { display:flex; gap:.5rem; margin-top:1rem; }
.modal .actions button, .chat-actions button { flex:1; padding:.6rem; border:none; border-radius:8px; cursor:pointer; }
.modal .actions button:nth-child(1), .chat-actions button:nth-child(1) { background:var(--primary); color:#fff; }
.modal-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,.4); }
.modal-overlay.active { display:block; }
.chatbox { bottom:1rem; right:1rem; width:min(90%,360px); z-index:50; }
.chat-body { height:340px; display:flex; flex-direction:column; gap:.5rem; }
#chatMessages { flex:1; overflow:auto; display:flex; flex-direction:column; gap:.5rem; font-size:.9rem; }
#chatMessages .me { align-self:flex-end; background:var(--primary); color:#fff; padding:.5rem .75rem; border-radius:12px 12px 0 12px; max-width:80%; }
#chatMessages .bot { align-self:flex-start; background:#e2e8f0; padding:.5rem .75rem; border-radius:12px 12px 12px 0; max-width:80%; }
#chatInput { resize:none; height:60px; }
.chat-toggle { position:fixed; bottom:1rem; right:1rem; background:var(--primary); color:#fff; width:3.5rem; height:3.5rem; border-radius:50%; border:none; cursor:pointer; font-size:1.5rem; z-index:40; }
.toast { position:fixed; top:1rem; left:50%; transform:translateX(-50%); background:#10b981; color:#fff; padding:.75rem 1.25rem; border-radius:8px; display:none; }
footer { text-align:center; padding:2rem 1rem; color:#64748b; font-size:.85rem; }
</style>
</head>
<body>
<header><h1>👟 Toko Sepatu Online</h1><p>Sepatu original, gratis ongkir, CS AI siap bantu!</p></header>
<main>
  <h2>Produk Terlaris</h2>
  <div class="products" id="products"></div>
</main>

<div class="modal-overlay" id="overlay"></div>
<div class="modal" id="orderModal">
  <h2>🛒 Formulir Pesanan</h2>
  <form id="orderForm">
    <p id="orderInfo"></p>
    <label>Nama Lengkap</label><input name="name" required />
    <label>Nomor HP</label><input name="phone" required />
    <label>Alamat Pengiriman</label><textarea name="address" required></textarea>
    <label>Jumlah</label><input type="number" name="quantity" min="1" value="1" required />
    <div class="actions">
      <button type="submit">Pesan Sekarang</button>
      <button type="button" onclick="closeModal()">Batal</button>
    </div>
  </form>
</div>

<button class="chat-toggle" onclick="toggleChat()">💬</button>
<div class="chatbox" id="chatbox">
  <div class="chat-head">CS AI - Tanya sepuasnya</div>
  <div class="chat-body">
    <div id="chatMessages"></div>
    <textarea id="chatInput" placeholder="Tulis pesan..."></textarea>
    <div class="chat-actions"><button onclick="sendChat()">Kirim</button></div>
  </div>
</div>

<div class="toast" id="toast"></div>
<footer>© Toko Sepatu Online — dibuat dengan AI 🤖</footer>

<script>
let products = [];
let selectedProduct = null;

async function loadProducts() {
  const res = await fetch('/api/products');
  products = await res.json();
  const container = document.getElementById('products');
  container.innerHTML = products.map(p => \`
    <div class="product">
      <img src="\${p.image}" alt="\${p.name}">
      <div class="info">
        <h3>\${p.name}</h3>
        <div class="brand">\${p.brand}</div>
        <div class="price">Rp\${Number(p.price).toLocaleString('id-ID')}</div>
        <button onclick="openOrder(\${p.id})">Beli</button>
      </div>
    </div>
  \`).join('');
}

function openOrder(id) {
  selectedProduct = products.find(p => p.id === id);
  document.getElementById('orderInfo').innerText = \`\${selectedProduct.name} — Rp\${Number(selectedProduct.price).toLocaleString('id-ID')}\`;
  document.getElementById('overlay').classList.add('active');
  document.getElementById('orderModal').classList.add('active');
}
function closeModal() {
  document.getElementById('overlay').classList.remove('active');
  document.getElementById('orderModal').classList.remove('active');
}

document.getElementById('orderForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const quantity = Number(fd.get('quantity'));
  const res = await fetch('/api/order', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: selectedProduct.id,
      name: fd.get('name'), phone: fd.get('phone'), address: fd.get('address'), quantity
    })
  });
  const data = await res.json();
  if (data.ok) {
    showToast(\`Pesanan #\${data.order_id.slice(0,8)} berhasil! Total Rp\${data.total.toLocaleString('id-ID')}\`);
    closeModal();
    e.target.reset();
  } else {
    showToast(data.error || 'Gagal memesan');
  }
});

function toggleChat() { document.getElementById('chatbox').classList.toggle('active'); }
document.getElementById('chatInput').addEventListener('keydown', e => { if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendChat(); }});

async function sendChat() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;
  appendMessage('me', text);
  input.value = '';
  const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text }) });
  const data = await res.json();
  appendMessage('bot', data.reply || 'Maaf, saya sedang sibuk.');
}
function appendMessage(who, text) {
  const msgs = document.getElementById('chatMessages');
  const div = document.createElement('div'); div.className = who; div.innerText = text;
  msgs.appendChild(div); msgs.scrollTop = msgs.scrollHeight;
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.innerText = msg; t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3000);
}

loadProducts();
fetch('/api/init');
</script>
</body>
</html>`;
