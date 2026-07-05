const HTML = `<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SendalQu - Toko Sendal Modern</title>
  <style>
    :root{--primary:#0ea5e9;--primary-dark:#0284c7;--bg:#f8fafc;--card:#ffffff;--text:#0f172a;--muted:#64748b;--accent:#f59e0b;--danger:#ef4444;--success:#22c55e;--shadow:0 4px 6px -1px rgba(0,0,0,0.1),0 2px 4px -2px rgba(0,0,0,0.1);--shadow-lg:0 10px 15px -3px rgba(0,0,0,0.1),0 4px 6px -4px rgba(0,0,0,0.1);}
    *{box-sizing:border-box;margin:0;padding:0}
    html{scroll-behavior:smooth}
    body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
    a{text-decoration:none;color:inherit}
    button{font-family:inherit;cursor:pointer;border:none}
    img{max-width:100%;display:block;border-radius:18px}
    .container{max-width:1200px;margin:0 auto;padding:0 20px}
    header{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-dark) 100%);color:#fff;padding:16px 0;position:sticky;top:0;z-index:50;box-shadow:var(--shadow)}
    .nav{display:flex;align-items:center;justify-content:space-between;gap:16px}
    .logo{font-size:1.5rem;font-weight:800;display:flex;align-items:center;gap:8px}
    .logo span{font-size:1.8rem}
    .nav-links{display:none;gap:24px;align-items:center}
    .nav-links a{font-weight:500;opacity:.9;transition:opacity .2s}
    .nav-links a:hover{opacity:1}
    .btn{background:#fff;color:var(--primary-dark);padding:10px 18px;border-radius:99px;font-weight:700;transition:transform .2s,box-shadow .2s;box-shadow:var(--shadow)}
    .btn:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg)}
    .hero{padding:80px 0 60px;background:linear-gradient(135deg,#e0f2fe 0%,#f0f9ff 100%)}
    .hero-grid{display:grid;grid-template-columns:1fr;gap:40px;align-items:center}
    .hero h1{font-size:2.3rem;line-height:1.15;font-weight:900;margin-bottom:16px;color:#0f172a}
    .hero h1 span{color:var(--primary-dark)}
    .hero p{font-size:1.1rem;color:var(--muted);margin-bottom:28px;max-width:520px}
    .hero-btns{display:flex;gap:14px;flex-wrap:wrap}
    .btn-primary{background:var(--primary);color:#fff;padding:14px 28px;border-radius:99px;font-weight:700;font-size:1rem;box-shadow:var(--shadow);transition:transform .2s,background .2s;display:inline-block}
    .btn-primary:hover{background:var(--primary-dark);transform:translateY(-2px)}
    .btn-outline{background:transparent;color:var(--primary-dark);border:2px solid var(--primary-dark);padding:14px 28px;border-radius:99px;font-weight:700;transition:background .2s,color .2s}
    .btn-outline:hover{background:var(--primary-dark);color:#fff}
    .hero-img img{box-shadow:var(--shadow-lg);transition:transform .4s}
    .hero-img img:hover{transform:rotate(-1deg)}
    .features{padding:60px 0;background:#fff}
    .features-grid{display:grid;grid-template-columns:1fr;gap:24px}
    .feature-card{background:var(--bg);padding:28px;border-radius:20px;text-align:center;transition:transform .2s,box-shadow .2s}
    .feature-card:hover{transform:translateY(-5px);box-shadow:var(--shadow-lg)}
    .feature-icon{font-size:2.5rem;margin-bottom:14px}
    .feature-card h3{font-size:1.15rem;margin-bottom:8px}
    .feature-card p{font-size:.95rem;color:var(--muted)}
    .section{padding:70px 0}
    .section-header{text-align:center;margin-bottom:42px}
    .section-header h2{font-size:1.9rem;font-weight:800;margin-bottom:10px}
    .section-header p{color:var(--muted)}
    .products-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
    .product-card{background:var(--card);border-radius:20px;overflow:hidden;box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s;display:flex;flex-direction:column}
    .product-card:hover{transform:translateY(-6px);box-shadow:var(--shadow-lg)}
    .product-img{height:160px;background:linear-gradient(135deg,#e2e8f0,#f1f5f9);display:grid;place-items:center;font-size:4rem;position:relative}
    .badge{position:absolute;top:12px;left:12px;background:var(--accent);color:#fff;font-size:.7rem;font-weight:700;padding:5px 10px;border-radius:99px}
    .badge.new{background:var(--success)}
    .product-body{padding:18px;display:flex;flex-direction:column;gap:8px;flex:1}
    .product-body h3{font-size:.98rem;font-weight:700}
    .product-body p{font-size:.82rem;color:var(--muted)}
    .price{font-size:1.15rem;font-weight:800;color:var(--primary-dark)}
    .price s{font-size:.85rem;color:var(--muted);font-weight:500;margin-left:6px}
    .add-to-cart{background:var(--primary);color:#fff;padding:12px 0;border-radius:12px;font-weight:700;transition:background .2s;width:100%;margin-top:auto}
    .add-to-cart:hover{background:var(--primary-dark)}
    @media(min-width:640px){.products-grid{grid-template-columns:repeat(3,1fr);gap:22px}.hero h1{font-size:2.8rem}}
    @media(min-width:1024px){.nav-links{display:flex}.hero-grid{grid-template-columns:1.1fr .9fr}.features-grid{grid-template-columns:repeat(4,1fr)}.products-grid{grid-template-columns:repeat(4,1fr)}.hero h1{font-size:3.3rem}}
    .chat-float{position:fixed;bottom:24px;right:24px;z-index:100}
    .chat-btn{background:var(--primary);color:#fff;width:62px;height:62px;border-radius:50%;display:grid;place-items:center;box-shadow:var(--shadow-lg);transition:transform .2s}
    .chat-btn:hover{transform:scale(1.08)}
    .chat-btn svg{width:30px;height:30px}
    .chat-box{position:absolute;bottom:80px;right:0;width:min(360px,calc(100vw - 40px));height:520px;background:var(--card);border-radius:24px;box-shadow:var(--shadow-lg);display:flex;flex-direction:column;overflow:hidden;transform:scale(.9);opacity:0;visibility:hidden;transition:all .25s;transform-origin:bottom right}
    .chat-box.open{transform:scale(1);opacity:1;visibility:visible}
    .chat-header{background:linear-gradient(135deg,var(--primary),var(--primary-dark));color:#fff;padding:16px 20px;display:flex;align-items:center;justify-content:space-between}
    .chat-header div h4{font-size:1rem}.chat-header div p{font-size:.8rem;opacity:.85}.chat-header button{background:none;color:#fff;font-size:1.4rem;line-height:1}
    .chat-messages{flex:1;padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;background:#f8fafc}
    .msg{max-width:82%;padding:12px 16px;border-radius:18px;font-size:.92rem;line-height:1.45;animation:pop .25s ease}
    @keyframes pop{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
    .msg.bot{align-self:flex-start;background:#fff;color:var(--text);border-bottom-left-radius:6px;box-shadow:var(--shadow)}
    .msg.user{align-self:flex-end;background:var(--primary);color:#fff;border-bottom-right-radius:6px}
    .typing{display:flex;gap:5px;padding:14px 16px;background:#fff;border-radius:18px;border-bottom-left-radius:6px;box-shadow:var(--shadow);align-self:flex-start}
    .typing span{width:8px;height:8px;background:var(--primary);border-radius:50%;animation:bounce 1.4s infinite ease-in-out}
    .typing span:nth-child(2){animation-delay:.2s}.typing span:nth-child(3){animation-delay:.4s}
    @keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
    .chat-form{padding:14px;background:#fff;border-top:1px solid #e2e8f0;display:flex;gap:10px}
    .chat-form input{flex:1;padding:12px 16px;border:1px solid #cbd5e1;border-radius:99px;font-size:.95rem;outline:none}
    .chat-form input:focus{border-color:var(--primary)}
    .chat-form button{background:var(--primary);color:#fff;width:42px;border-radius:50%;display:grid;place-items:center;transition:background .2s}
    .chat-form button:hover{background:var(--primary-dark)}
    .cart-overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:80;opacity:0;visibility:hidden;transition:opacity .2s}.cart-overlay.open{opacity:1;visibility:visible}
    .cart-drawer{position:fixed;top:0;right:0;width:min(420px,100vw);height:100%;background:var(--card);box-shadow:var(--shadow-lg);z-index:90;transform:translateX(100%);transition:transform .3s;display:flex;flex-direction:column}.cart-drawer.open{transform:translateX(0)}
    .cart-head{padding:22px;border-bottom:1px solid #e2e8f0;display:flex;align-items:center;justify-content:space-between}.cart-head h3{font-size:1.2rem}.cart-head button{background:none;font-size:1.6rem;color:var(--muted)}
    .cart-items{flex:1;overflow-y:auto;padding:20px}.cart-empty{text-align:center;color:var(--muted);margin-top:60px}
    .cart-item{display:flex;gap:14px;align-items:center;margin-bottom:18px}.cart-item .thumb{width:56px;height:56px;border-radius:12px;background:#e2e8f0;display:grid;place-items:center;font-size:1.6rem}.cart-item .info{flex:1}.cart-item .info h4{font-size:.95rem}.cart-item .info p{font-size:.85rem;color:var(--muted)}.cart-item .qty{display:flex;align-items:center;gap:8px}.cart-item .qty button{width:28px;height:28px;border-radius:6px;background:#f1f5f9;color:var(--text);font-weight:700}
    .cart-foot{padding:22px;border-top:1px solid #e2e8f0}.cart-total{display:flex;justify-content:space-between;font-size:1.2rem;font-weight:800;margin-bottom:14px}.checkout{background:var(--success);color:#fff;padding:14px 0;border-radius:12px;font-weight:700;width:100%;font-size:1rem;transition:opacity .2s}.checkout:hover{opacity:.9}
    .toast{position:fixed;top:24px;left:50%;transform:translateX(-50%) translateY(-80px);background:#0f172a;color:#fff;padding:14px 24px;border-radius:99px;box-shadow:var(--shadow-lg);z-index:110;display:flex;align-items:center;gap:10px;font-weight:600;transition:transform .35s}.toast.show{transform:translateX(-50%) translateY(0)}
    .reviews-grid{display:grid;grid-template-columns:1fr;gap:20px}.review-card{background:var(--card);padding:24px;border-radius:20px;box-shadow:var(--shadow)}.stars{color:var(--accent);margin-bottom:10px}.review-card p{color:var(--muted);font-size:.95rem;margin-bottom:12px}.reviewer{font-weight:700}
    @media(min-width:640px){.reviews-grid{grid-template-columns:repeat(2,1fr)}}@media(min-width:1024px){.reviews-grid{grid-template-columns:repeat(3,1fr)}}
    footer{background:#0f172a;color:#94a3b8;padding:40px 0 24px;text-align:center}footer .social{display:flex;justify-content:center;gap:16px;margin-top:14px}footer .social a{font-size:1.5rem;transition:color .2s}footer .social a:hover{color:#fff}
  </style>
</head>
<body>
  <header><div class="container nav"><a href="#" class="logo"><span>👡</span> SendalQu</a>
    <nav class="nav-links"><a href="#produk">Produk</a><a href="#ulasan">Ulasan</a><a href="#kontak">Kontak</a></nav>
    <div style="display:flex;align-items:center;gap:12px"><button onclick="toggleCart()" style="background:rgba(255,255,255,.2);color:#fff;padding:10px 16px;border-radius:99px;font-weight:700">🛒 <span id="cartCountTop">0</span></button></div>
  </div></header>

  <section class="hero"><div class="container hero-grid"><div>
    <h1>Langkah Nyaman Setiap Hari <span>Bersama SendalQu</span></h1>
    <p>Koleksi sendal modern dengan desain kekinian, ringan, anti-slip, dan harga bersahabat. Pengiriman cepat ke seluruh Indonesia.</p>
    <div class="hero-btns"><a href="#produk" class="btn-primary">Belanja Sekarang</a><a href="#ulasan" class="btn-outline">Lihat Ulasan</a></div>
  </div><div class="hero-img"><img src="https://images.unsplash.com/photo-1603487742131-4160ec999306?auto=format&fit=crop&w=600&q=80" alt="Sendal modern"></div></div></section>

  <section class="features"><div class="container features-grid">
    <div class="feature-card"><div class="feature-icon">🚚</div><h3>Gratis Ongkir</h3><p>Pembelian di atas Rp150.000</p></div>
    <div class="feature-card"><div class="feature-icon">🔄</div><h3>Garansi Tukar</h3><p>Salah ukuran? Tukar 7 hari</p></div>
    <div class="feature-card"><div class="feature-icon">💬</div><h3>CS AI 24/7</h3><p>Tanya stok & ukuran</p></div>
    <div class="feature-card"><div class="feature-icon">⭐</div><h3>Kualitas Terbaik</h3><p>Bahan premium tahan lama</p></div>
  </div></section>

  <section class="section" id="produk"><div class="container">
    <div class="section-header"><h2>Koleksi Sendal Pilihan</h2><p>Desain modern, nyaman dipakai seharian</p></div>
    <div class="products-grid" id="productsGrid"></div>
  </div></section>

  <section class="section" id="ulasan" style="background:#fff"><div class="container">
    <div class="section-header"><h2>Apa Kata Pelanggan</h2><p>Ulasan jujur dari pembeli SendalQu</p></div>
    <div class="reviews-grid">
      <div class="review-card"><div class="stars">★★★★★</div><p>"Sendalnya empuk banget, cocok buat jalan-jalan seharian. Pengiriman juga cepat!"</p><div class="reviewer">— Rina, Jakarta</div></div>
      <div class="review-card"><div class="stars">★★★★★</div><p>"Warna pastelnya lucu, pas buat OOTD. Harganya worth it."</p><div class="reviewer">— Dita, Bandung</div></div>
      <div class="review-card"><div class="stars">★★★★☆</div><p>"Sole anti slip-nya beneran works. Recommended!"</p><div class="reviewer">— Budi, Surabaya</div></div>
    </div>
  </div></section>

  <section class="section" id="kontak"><div class="container">
    <div class="section-header"><h2>Hubungi Kami</h2><p>Punya pertanyaan? CS AI siap membantu</p></div>
    <div class="features-grid" style="max-width:800px;margin:0 auto">
      <div class="feature-card"><div class="feature-icon">📧</div><h3>Email</h3><p>hai@sendalqu.id</p></div>
      <div class="feature-card"><div class="feature-icon">📱</div><h3>WhatsApp</h3><p>0812-3456-7890</p></div>
      <div class="feature-card"><div class="feature-icon">📍</div><h3>Alamat</h3><p>Jl. Nyaman No. 1, Jakarta</p></div>
    </div>
  </div></section>

  <footer><div class="container"><p>&copy; 2024 SendalQu. Sendal modern untukmu.</p>
    <div class="social"><a href="#">📘</a><a href="#">📸</a><a href="#">🐦</a></div>
  </div></footer>

  <div class="chat-float">
    <div class="chat-box" id="chatBox">
      <div class="chat-header"><div><h4>SendalQu Assistant</h4><p>Online 24 jam</p></div><button onclick="toggleChat()">&times;</button></div>
      <div class="chat-messages" id="chatMessages"><div class="msg bot">Halo! Saya asisten SendalQu. Mau tanya produk, ukuran, atau cara order?</div></div>
      <form class="chat-form" onsubmit="sendMessage(event)"><input id="chatInput" placeholder="Tulis pertanyaanmu..." autocomplete="off"><button type="submit">➤</button></form>
    </div>
    <button class="chat-btn" onclick="toggleChat()" aria-label="Chat AI CS"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.77 9.77 0 0 1-4-.85L3 20l1.85-3.2A8.96 8.96 0 0 1 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8Z"/></svg></button>
  </div>

  <div class="cart-overlay" id="cartOverlay" onclick="toggleCart()"></div>
  <div class="cart-drawer" id="cartDrawer">
    <div class="cart-head"><h3>🛒 Keranjangmu</h3><button onclick="toggleCart()">&times;</button></div>
    <div class="cart-items" id="cartItems"><div class="cart-empty">Keranjang masih kosong</div></div>
    <div class="cart-foot"><div class="cart-total"><span>Total</span><span id="cartTotal">Rp0</span></div><button class="checkout" onclick="checkout()">Checkout</button></div>
  </div>
  <div class="toast" id="toast">✅ Produk ditambahkan!</div>

  <script>
    const products=[
      {id:1,name:"Sendal Slide Cloud",emoji:"☁️",desc:"Sole empuk seperti awan",price:129000,old:159000,badge:"BEST"},
      {id:2,name:"Sendal Nordic",emoji:"🌿",desc:"Minimalis anti-slip",price:145000,old:179000,badge:""},
      {id:3,name:"Sendal Urban Kpop",emoji:"🩴",desc:"Trendy pastel kekinian",price:98000,old:125000,badge:"NEW"},
      {id:4,name:"Sendal Yogyak",emoji:"🏝️",desc:"Buat jalan-jalan santai",price:110000,old:139000,badge:""},
      {id:5,name:"Sendal Sporty",emoji:"🏃",desc:"Lentur & ringan",price:155000,old:189000,badge:""},
      {id:6,name:"Sendal Homey",emoji:"🏠",desc:"Nyaman dipakai di rumah",price:85000,old:109000,badge:""},
      {id:7,name:"Sendal Beach Vibes",emoji:"🐚",desc:"Waterproof pantai",price:119000,old:149000,badge:"NEW"},
      {id:8,name:"Sendal Classic",emoji:"🥿",desc:"Timeless & elegan",price:135000,old:169000,badge:"BEST"}
    ];
    let cart=JSON.parse(localStorage.getItem('sendalqu_cart')||'[]');
    function fmt(n){return 'Rp'+n.toLocaleString('id');}
    function cardHTML(p){
      const bdg = p.badge ? '<span class="badge '+ (p.badge==='NEW'?'new ':'')+'">'+p.badge+'</span>' : '';
      return '<div class="product-card"><div class="product-img"><span>'+p.emoji+'</span>'+bdg+'</div><div class="product-body"><h3>'+p.name+'</h3><p>'+p.desc+'</p><div class="price">'+fmt(p.price)+'<s>'+fmt(p.old)+'</s></div><button class="add-to-cart" onclick="addToCart('+p.id+')">Tambah ke Keranjang</button></div></div>';
    }
    function renderProducts(){document.getElementById('productsGrid').innerHTML=products.map(cardHTML).join('');}
    function saveCart(){localStorage.setItem('sendalqu_cart',JSON.stringify(cart));updateCartUI();}
    function addToCart(id){const p=products.find(x=>x.id===id);const item=cart.find(x=>x.id===id);if(item)item.qty++;else cart.push({...p,qty:1});saveCart();showToast(p.name+' ditambahkan');}
    function cartItemHTML(i){return '<div class="cart-item"><div class="thumb">'+i.emoji+'</div><div class="info"><h4>'+i.name+'</h4><p>'+fmt(i.price)+'</p></div><div class="qty"><button onclick="changeQty('+i.id+',-1)">-</button><span>'+i.qty+'</span><button onclick="changeQty('+i.id+',1)">+</button></div></div>';}
    function updateCartUI(){
      const count=cart.reduce((a,b)=>a+b.qty,0);document.getElementById('cartCountTop').textContent=count;
      const items=document.getElementById('cartItems');
      if(!count){items.innerHTML='<div class="cart-empty">Keranjang masih kosong</div>';document.getElementById('cartTotal').textContent='Rp0';return;}
      items.innerHTML=cart.map(cartItemHTML).join('');
      document.getElementById('cartTotal').textContent=fmt(cart.reduce((a,b)=>a+b.price*b.qty,0));
    }
    function changeQty(id,d){const i=cart.find(x=>x.id===id);if(i){i.qty+=d;if(i.qty<=0)cart=cart.filter(x=>x.id!==id);saveCart();}}
    function toggleCart(){document.getElementById('cartDrawer').classList.toggle('open');document.getElementById('cartOverlay').classList.toggle('open');}
    function checkout(){if(!cart.length){showToast('Keranjang kosong!');return;}cart=[];saveCart();toggleCart();showToast('Checkout berhasil! Terima kasih 🎉');}
    function toggleChat(){document.getElementById('chatBox').classList.toggle('open');}
    async function sendMessage(e){e.preventDefault();const input=document.getElementById('chatInput');const text=input.value.trim();if(!text)return;appendMsg(text,'user');input.value='';const typing=document.createElement('div');typing.className='typing';typing.id='typing';typing.innerHTML='<span></span><span></span><span></span>';document.getElementById('chatMessages').appendChild(typing);scrollChat();
      try{const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});const data=await res.json();typing.remove();appendMsg(data.reply||'Maaf, saya belum mengerti.','bot');}
      catch(err){typing.remove();appendMsg('Maaf, sedang ada gangguan. Coba lagi ya!','bot');}}
    function appendMsg(text,from){const div=document.createElement('div');div.className='msg '+from;div.textContent=text;document.getElementById('chatMessages').appendChild(div);scrollChat();}
    function scrollChat(){const m=document.getElementById('chatMessages');m.scrollTop=m.scrollHeight;}
    function showToast(text){const t=document.getElementById('toast');t.textContent='✅ '+text;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2400);}
    renderProducts();updateCartUI();
  </script>
</body>
</html>`;

const PRODUCTS = [
  {id:1,name:"Sendal Slide Cloud",emoji:"☁️",desc:"Sole empuk seperti awan",price:129000,old:159000,badge:"BEST"},
  {id:2,name:"Sendal Nordic",emoji:"🌿",desc:"Minimalis anti-slip",price:145000,old:179000,badge:""},
  {id:3,name:"Sendal Urban Kpop",emoji:"🩴",desc:"Trendy pastel kekinian",price:98000,old:125000,badge:"NEW"},
  {id:4,name:"Sendal Yogyak",emoji:"🏝️",desc:"Buat jalan-jalan santai",price:110000,old:139000,badge:""},
  {id:5,name:"Sendal Sporty",emoji:"🏃",desc:"Lentur & ringan",price:155000,old:189000,badge:""},
  {id:6,name:"Sendal Homey",emoji:"🏠",desc:"Nyaman dipakai di rumah",price:85000,old:109000,badge:""},
  {id:7,name:"Sendal Beach Vibes",emoji:"🐚",desc:"Waterproof pantai",price:119000,old:149000,badge:"NEW"},
  {id:8,name:"Sendal Classic",emoji:"🥿",desc:"Timeless & elegan",price:135000,old:169000,badge:"BEST"}
];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'GET' && url.pathname === '/') {
      return new Response(HTML, { headers: { 'Content-Type': 'text/html;charset=UTF-8' } });
    }
    if (url.pathname === '/api/chat' && request.method === 'POST') {
      try {
        const { message } = await request.json();
        const catalog = PRODUCTS.map(p => p.name + ' - ' + p.price.toLocaleString('id') + ' (' + p.desc + ')').join('\n');
        const messages = [
          { role: 'system', content: 'Kamu adalah customer service AI ramah untuk toko SendalQu. Jawab dalam Bahasa Indonesia yang santai. Kamu tahu katalog produk ini:\n' + catalog + '\nPromo: gratis ongkir pembelian di atas Rp150.000, garansi tukar 7 hari. Bantu pelanggan memilih ukuran, warna, dan proses order.' },
          { role: 'user', content: message }
        ];
        const ai = await env.AI.run('@cf/moonshotai/kimi-k2.6', { messages });
        const reply = ai.choices[0].message.content;
        return new Response(JSON.stringify({ reply }), { headers: { 'Content-Type': 'application/json' } });
      } catch (err) {
        return new Response(JSON.stringify({ reply: 'Maaf layanan AI sedang sibuk, coba beberapa saat lagi ya.' }), { headers: { 'Content-Type': 'application/json' }, status: 500 });
      }
    }
    return new Response('Not found', { status: 404 });
  }
};
