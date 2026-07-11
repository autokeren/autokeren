const RECOMMENDATIONS_TABLE = `
  CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    roast TEXT,
    flavor TEXT,
    method TEXT,
    budget TEXT,
    blend_name TEXT,
    description TEXT,
    brew_guide TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`;

const CHAT_TABLE = `
  CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT,
    message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`;

async function initDB(db) {
  await db.prepare(RECOMMENDATIONS_TABLE).run();
  await db.prepare(CHAT_TABLE).run();
}

function renderHTML() {
  return `<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kopi Juara AI — Ciptakan Racikan Kopi Juaramu</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <style>
    :root {
      --primary: #3e2723;
      --primary-light: #5d4037;
      --bg: #0f0c0b;
      --card: #1a1513;
      --surface: #241e1c;
      --text: #f5f0eb;
      --muted: #a89f9a;
      --accent: #ffb300;
      --accent-2: #ff7043;
      --success: #66bb6a;
      --radius: 18px;
      --shadow: 0 20px 60px rgba(0,0,0,0.45);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }
    .container { width: min(1100px, 92%); margin: 0 auto; }
    .navbar {
      position: sticky; top: 0; z-index: 50;
      background: rgba(15,12,11,0.85);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid rgba(255,179,0,0.12);
    }
    .nav-inner { display: flex; align-items: center; justify-content: space-between; padding: 1rem 0; }
    .logo { font-size: 1.35rem; font-weight: 800; color: var(--accent); text-decoration: none; }
    .nav-links { display: flex; gap: 1.5rem; }
    .nav-links a { color: var(--muted); text-decoration: none; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover { color: var(--text); }
    .hero { padding: 6rem 0 5rem; }
    .hero-inner { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 3rem; align-items: center; }
    .badge {
      display: inline-block; padding: 0.35rem 0.85rem; border-radius: 999px;
      background: rgba(255,179,0,0.12); color: var(--accent); font-weight: 700; font-size: 0.8rem; margin-bottom: 1rem;
    }
    .hero h1 { font-size: clamp(2.3rem, 5vw, 3.6rem); line-height: 1.1; margin-bottom: 1rem; }
    .hero p { font-size: 1.15rem; color: var(--muted); margin-bottom: 2rem; max-width: 520px; }
    .btn {
      display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.85rem 1.7rem; border: none;
      border-radius: 999px; font-weight: 700; cursor: pointer; font-size: 1rem; transition: transform 0.15s, box-shadow 0.2s;
    }
    .btn:hover { transform: translateY(-2px); }
    .btn-primary {
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #1a120b; box-shadow: 0 10px 30px rgba(255,179,0,0.25);
    }
    .btn-secondary {
      background: var(--surface); color: var(--text); border: 1px solid rgba(255,255,255,0.08);
    }
    .coffee-card {
      position: relative; background: var(--card); border-radius: var(--radius); padding: 2rem;
      box-shadow: var(--shadow); border: 1px solid rgba(255,179,0,0.15); overflow: hidden;
      aspect-ratio: 1/1; display: flex; align-items: center; justify-content: center;
    }
    .coffee-swirl {
      width: 220px; height: 220px; border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #6d4c41 0%, #3e2723 45%, #1a100e 90%);
      box-shadow: inset -20px -20px 40px rgba(0,0,0,0.6);
      animation: swirl 14s linear infinite;
    }
    @keyframes swirl { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .label-preview {
      position: absolute; bottom: 1.5rem; left: 1.5rem; right: 1.5rem;
      background: rgba(15,12,11,0.85); border: 1px solid rgba(255,179,0,0.2);
      border-radius: 12px; padding: 1rem; text-align: center;
    }
    .label-preview strong { display: block; color: var(--accent); font-size: 1.1rem; }
    .label-preview small { color: var(--muted); }
    .section-title { text-align: center; font-size: clamp(1.6rem, 3.5vw, 2.2rem); margin-bottom: 0.6rem; }
    .section-subtitle { text-align: center; color: var(--muted); margin-bottom: 2.4rem; }
    .features { padding: 4rem 0; background: linear-gradient(180deg, rgba(255,179,0,0.03), transparent); }
    .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem; }
    .feature-card {
      background: var(--card); border: 1px solid rgba(255,255,255,0.06); border-radius: var(--radius);
      padding: 1.8rem; transition: transform 0.2s, border-color 0.2s;
    }
    .feature-card:hover { transform: translateY(-5px); border-color: rgba(255,179,0,0.3); }
    .feature-card .icon { font-size: 2rem; margin-bottom: 0.8rem; }
    .feature-card h3 { margin-bottom: 0.5rem; }
    .feature-card p { color: var(--muted); font-size: 0.95rem; }
    .quiz-section { padding: 5rem 0; }
    .quiz-form {
      background: var(--card); border: 1px solid rgba(255,255,255,0.06); border-radius: var(--radius);
      padding: 2rem; max-width: 640px; margin: 0 auto;
    }
    .quiz-step { display: none; animation: fade 0.25s ease; }
    .quiz-step.active { display: block; }
    @keyframes fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .quiz-step label { display: block; font-weight: 600; margin-bottom: 1rem; font-size: 1.05rem; }
    .quiz-step input[type="text"] {
      width: 100%; padding: 0.9rem 1rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);
      background: var(--surface); color: var(--text); margin-bottom: 1.5rem; font-size: 1rem;
    }
    .option-group { display: grid; gap: 0.75rem; }
    .option {
      padding: 0.9rem 1rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);
      background: var(--surface); color: var(--text); cursor: pointer; text-align: left; font-size: 0.95rem;
      transition: all 0.15s;
    }
    .option:hover, .option.selected {
      border-color: var(--accent); background: rgba(255,179,0,0.1); color: var(--accent);
    }
    .quiz-nav { display: flex; justify-content: space-between; margin-top: 2rem; }
    .result { margin-top: 2rem; }
    .result.hidden { display: none; }
    .result-card {
      background: var(--card); border: 1px solid rgba(255,179,0,0.25); border-radius: var(--radius);
      padding: 2rem; max-width: 640px; margin: 0 auto; box-shadow: var(--shadow);
    }
    .result-card h3 { text-align: center; color: var(--accent); margin-bottom: 1.5rem; }
    .blend-name { font-size: 1.7rem; font-weight: 800; text-align: center; margin-bottom: 0.6rem; }
    .blend-tagline { text-align: center; color: var(--muted); margin-bottom: 1.5rem; }
    .blend-section { margin-bottom: 1.5rem; }
    .blend-section h4 { color: var(--accent-2); margin-bottom: 0.5rem; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.04em; }
    .blend-section p { color: var(--text); font-size: 0.98rem; line-height: 1.7; white-space: pre-line; }
    .chat-section { padding: 5rem 0 6rem; background: linear-gradient(180deg, transparent, rgba(255,179,0,0.03)); }
    .chat-box {
      background: var(--card); border: 1px solid rgba(255,255,255,0.06); border-radius: var(--radius);
      min-height: 320px; max-height: 440px; overflow-y: auto; padding: 1.2rem; margin-bottom: 1rem;
    }
    .chat-msg { margin-bottom: 1rem; display: flex; flex-direction: column; }
    .chat-msg.user { align-items: flex-end; }
    .chat-msg.assistant { align-items: flex-start; }
    .chat-bubble {
      max-width: 80%; padding: 0.8rem 1.1rem; border-radius: 14px; font-size: 0.97rem; line-height: 1.6;
    }
    .chat-msg.user .chat-bubble { background: var(--accent); color: #1a120b; border-bottom-right-radius: 4px; }
    .chat-msg.assistant .chat-bubble { background: var(--surface); color: var(--text); border-bottom-left-radius: 4px; }
    .chat-form { display: flex; gap: 0.75rem; max-width: 800px; margin: 0 auto; }
    .chat-form input {
      flex: 1; padding: 0.9rem 1.1rem; border-radius: 999px; border: 1px solid rgba(255,255,255,0.1);
      background: var(--surface); color: var(--text); font-size: 1rem;
    }
    .typing { display: flex; gap: 0.35rem; padding: 0.75rem 1rem; }
    .typing span { width: 8px; height: 8px; background: var(--muted); border-radius: 50%; animation: bounce 1s infinite; }
    .typing span:nth-child(2) { animation-delay: 0.15s; }
    .typing span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes bounce { 0%, 80%, 100% { transform: translateY(0); } 40% { transform: translateY(-6px); } }
    .footer { text-align: center; padding: 2.5rem 0; color: var(--muted); border-top: 1px solid rgba(255,255,255,0.05); }
    @media (max-width: 820px) {
      .hero-inner { grid-template-columns: 1fr; }
      .hero-visual { order: -1; }
      .coffee-card { aspect-ratio: 16/10; }
      .nav-links { display: none; }
      .quiz-form, .result-card { padding: 1.4rem; }
    }
  </style>
</head>
<body>
  <nav class="navbar">
    <div class="container nav-inner">
      <a class="logo" href="#">☕ Kopi Juara</a>
      <div class="nav-links">
        <a href="#fitur">Fitur</a>
        <a href="#ai-blend">AI Blend</a>
        <a href="#chat">Tanya Barista AI</a>
      </div>
    </div>
  </nav>

  <section class="hero">
    <div class="container hero-inner">
      <div class="hero-text">
        <span class="badge">Powered by AI</span>
        <h1>Rutinitas Juara untuk Tubuhmu.</h1>
        <p>Kopi Juwara dengan Ekstrak Yung Kien Ganoderma + Yun Kim B. AI kami bantu susun pola konsumsi pribadi sesuai tujuan kesehatanmu.</p>
        <a href="#ai-routine" class="btn btn-primary">Rancang Rutinitas Juaramu</a>
      </div>
      <div class="hero-visual">
        <div class="coffee-card">
          <div class="coffee-swirl"></div>
          <div class="label-preview">
            <strong>Kopi Juwara</strong>
            <small>Arabika Brazil · VCO · YK Ganoderma</small>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="fitur" class="features">
    <div class="container">
      <h2 class="section-title">Mengapa Kombinasi Ini Juara?</h2>
      <div class="grid-3">
        <div class="feature-card">
          <div class="icon">☕</div>
          <h3>Kopi Juwara Premium</h3>
          <p>Biji kopi Arabika Brazil pilihan + krimer nabati VCO + Ekstrak Yung Kien Ganoderma murni.</p>
        </div>
        <div class="feature-card">
          <div class="icon">🌿</div>
          <h3>Yun Kim B / Yung Kien Ganoderma</h3>
          <p>Ekstrak Ganoderma lucidum dalam kapsul. Dosis standar 4 kapsul sehari untuk memelihara kesehatan.</p>
        </div>
        <div class="feature-card">
          <div class="icon">🤖</div>
          <h3>AI Rutinitas Personal</h3>
          <p>AI sesuaikan waktu dan takaran konsumsi Kopi Juwara + Yun Kim B berdasarkan tujuan kesehatanmu.</p>
        </div>
      </div>
    </div>
  </section>

  <section id="ai-routine" class="quiz-section">
    <div class="container quiz-inner">
      <h2 class="section-title">AI Rutinitas Juara</h2>
      <p class="section-subtitle">4 langkah susun pola konsumsi Kopi Juwara + Yun Kim B yang pas buat kamu.</p>
      <form id="quiz-form" class="quiz-form">
        <div class="quiz-step active" data-step="1">
          <label>1. Nama kamu</label>
          <input type="text" name="name" placeholder="Contoh: Andi" required>
          <label>Fokus kesehatan utama kamu?</label>
          <div class="option-group" data-name="goal">
            <button type="button" class="option" data-value="imun">Imun & daya tahan tubuh</button>
            <button type="button" class="option" data-value="energi">Energi & fokus beraktivitas</button>
            <button type="button" class="option" data-value="tidur">Relaksasi & kualitas tidur</button>
            <button type="button" class="option" data-value="pencernaan">Pencernaan & metabolisme</button>
          </div>
        </div>
        <div class="quiz-step" data-step="2">
          <label>2. Kebiasaan minum kopi harian?</label>
          <div class="option-group" data-name="habit">
            <button type="button" class="option" data-value="1x">1 gelas per hari</button>
            <button type="button" class="option" data-value="2x">2 gelas per hari</button>
            <button type="button" class="option" data-value="3x">3 gelas atau lebih</button>
            <button type="button" class="option" data-value="jarang">Jarang / baru mau coba</button>
          </div>
        </div>
        <div class="quiz-step" data-step="3">
          <label>3. Sensitivitas kafein?</label>
          <div class="option-group" data-name="caffeine">
            <button type="button" class="option" data-value="tinggi">Sensitif, jantung berdebar</button>
            <button type="button" class="option" data-value="normal">Normal, bisa 1–2 cangkir</button>
            <button type="button" class="option" data-value="rendah">Tidak masalah minum kopi malam</button>
          </div>
        </div>
        <div class="quiz-step" data-step="4">
          <label>4. Apakah saat ini mengonsumsi suplemen/herbal?</label>
          <div class="option-group" data-name="suplemen">
            <button type="button" class="option" data-value="ya">Ya</button>
            <button type="button" class="option" data-value="tidak">Tidak</button>
          </div>
        </div>
        <div class="quiz-nav">
          <button type="button" id="prev-btn" class="btn btn-secondary" disabled>Sebelumnya</button>
          <button type="button" id="next-btn" class="btn btn-primary">Selanjutnya</button>
        </div>
      </form>
      <div id="result" class="result hidden">
        <div class="result-card">
          <h3>🎉 Rutinitas Juara untukmu</h3>
          <div id="result-content"></div>
          <button class="btn btn-primary" id="order-btn">Konsultasi & Pesan via WhatsApp</button>
          <button class="btn btn-secondary" id="retry-btn">Coba Lagi</button>
        </div>
      </div>
    </div>
  </section>

  <section id="chat" class="chat-section">
    <div class="container">
      <h2 class="section-title">Tanya Ahli AI</h2>
      <p class="section-subtitle">Tanya soal Kopi Juwara, Yun Kim B, cara konsumsi, atau manfaat Ganoderma.</p>
      <div class="chat-box" id="chat-box"></div>
      <form id="chat-form" class="chat-form">
        <input type="text" id="chat-input" placeholder="Tanya sesuatu soal kopi..." required>
        <button type="submit" class="btn btn-primary">Kirim</button>
      </form>
    </div>
  </section>

  <footer class="footer">
    <div class="container">
      <p>© 2026 Kopi Juara AI. Dibuat dengan caffeine & AI.</p>
    </div>
  </footer>

  <script>
const selection = {};
    let currentStep = 1;
    const totalSteps = 4;
    const form = document.getElementById('quiz-form');
    const result = document.getElementById('result');
    const resultContent = document.getElementById('result-content');
    const nextBtn = document.getElementById('next-btn');
    const prevBtn = document.getElementById('prev-btn');

    function renderSteps() {
      document.querySelectorAll('.quiz-step').forEach(step => step.classList.toggle('active', Number(step.dataset.step) === currentStep));
      prevBtn.disabled = currentStep === 1;
      nextBtn.textContent = currentStep === totalSteps ? 'Temukan Blend' : 'Selanjutnya';
    }
    function updateButtonState() {
      const stepEl = document.querySelector('.quiz-step[data-step="' + currentStep + '"]');
      const group = stepEl.querySelector('.option-group');
      if (!group) { nextBtn.disabled = false; return; }
      const name = group.dataset.name;
      nextBtn.disabled = !selection[name];
    }
    document.querySelectorAll('.option-group').forEach(group => {
      group.querySelectorAll('.option').forEach(btn => {
        btn.addEventListener('click', () => {
          group.querySelectorAll('.option').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
          selection[group.dataset.name] = btn.dataset.value;
          updateButtonState();
        });
      });
    });
    nextBtn.addEventListener('click', async () => {
      if (currentStep < totalSteps) { currentStep++; renderSteps(); updateButtonState(); }
      else { await submitQuiz(); }
    });
    prevBtn.addEventListener('click', () => { if (currentStep > 1) { currentStep--; renderSteps(); updateButtonState(); } });
    updateButtonState();

    async function submitQuiz() {
      const name = form.querySelector('input[name="name"]').value.trim() || 'Sahabat Juara';
      const data = { name, goal: selection.goal, habit: selection.habit, caffeine: selection.caffeine, suplemen: selection.suplemen };
      nextBtn.disabled = true; nextBtn.textContent = 'AI Menyusun Rutinitas...';
      try {
        const res = await fetch('/api/recommend', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        const json = await res.json();
        form.classList.add('hidden');
        result.classList.remove('hidden');
        resultContent.innerHTML = '' +
          '<div class="blend-name">' + json.routine_name + '</div>' +
          '<div class="blend-tagline">Dibuat khusus untuk ' + json.name + '</div>' +
          '<div class="blend-section"><h4>Rekomendasi Produk</h4><p>' + json.product_recommendation + '</p></div>' +
          '<div class="blend-section"><h4>Jadwal Konsumsi Harian</h4><p>' + json.schedule + '</p></div>' +
          '<div class="blend-section"><h4>Catatan Penting</h4><p>' + json.notes + '</p></div>';
        document.getElementById('order-btn').onclick = () => {
          const text = encodeURIComponent('Halo Kopi Juara! Aku mau konsultasi soal rutinitas "' + json.routine_name + '" yang direkomendasikan AI.');
          window.open('https://wa.me/6281234567890?text=' + text, '_blank');
        };
      } catch (e) {
        nextBtn.textContent = 'Gagal, coba lagi';
      }
    }
    document.getElementById('retry-btn').addEventListener('click', () => {
      form.classList.remove('hidden'); result.classList.add('hidden');
      currentStep = 1; renderSteps(); updateButtonState();
    });

    const chatBox = document.getElementById('chat-box');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    function appendChat(role, text) {
      const msg = document.createElement('div'); msg.className = 'chat-msg ' + role;
      const bubble = document.createElement('div'); bubble.className = 'chat-bubble'; bubble.textContent = text;
      msg.appendChild(bubble); chatBox.appendChild(msg); chatBox.scrollTop = chatBox.scrollHeight;
    }
    appendChat('assistant', 'Halo! Aku Asisten AI Kopi Juara. Mau tanya soal Kopi Juwara, Yun Kim B, atau cara konsumsi yang tepat?');
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (!text) return;
      appendChat('user', text); chatInput.value = '';
      const typing = document.createElement('div'); typing.className = 'chat-msg assistant'; typing.innerHTML = '<div class="chat-bubble typing"><span></span><span></span><span></span></div>';
      chatBox.appendChild(typing); chatBox.scrollTop = chatBox.scrollHeight;
      try {
        const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text }) });
        const json = await res.json();
        typing.remove();
        appendChat('assistant', json.reply);
      } catch (err) {
        typing.remove();
        appendChat('assistant', 'Maaf, lagi ada gangguan. Coba lagi ya!');
      }
    });
  </script>
</body>
</html>`;
}

export default {
  async fetch(request, env) {
    await initDB(env.DB);
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "GET" && path === "/") {
      const html = renderHTML();
      return new Response(html, { headers: { "Content-Type": "text/html" } });
    }

if (request.method === "POST" && path === "/api/recommend") {
      const body = await request.json();
      const { name, goal, habit, caffeine, suplemen } = body;
      if (!goal || !habit || !caffeine) {
        return new Response(JSON.stringify({ error: "Semua pilihan harus diisi" }), { status: 400, headers: { "Content-Type": "application/json" } });
      }
      const prompt = `Kamu adalah ahli konsultan kesehatan untuk produk Kopi Juwara dan Yun Kim B (Yung Kien Ganoderma).

Data produk:
- Kopi Juwara: 3in1 kopi Arabika Brazil + krimer nabati VCO + Ekstrak Yung Kien Ganoderma (strain YK-01, dipatenkan, dari Shuang Hor Taiwan). Berbentuk ekstrak, bukan serbuk kasar. Mengandung senyawa aktif polisakarida, triterpenoid, antioksidan.
- Yun Kim B / Yung Kien Ganoderma: kapsul ekstrak Ganoderma lucidum. Dosis anjuran: 4 kapsul per hari. Fungsi: membantu memelihara kesehatan & memperlaras tubuh.
- Catatan: ini suplemen/kebugaran, bukan obat. Jangan klaim menyembuhkan penyakit. Anjurkan konsultasi dokter untuk kondisi medis.

Profil pengguna:
- Nama: ${name || "Sahabat Juara"}
- Tujuan kesehatan: ${goal}
- Kebiasaan kopi: ${habit} sehari
- Sensitivitas kafein: ${caffeine}
- Sudah konsumsi suplemen/herbal lain: ${suplemen || "tidak"}

Buatkan rutinitas konsumsi Kopi Juwara + Yun Kim B personal dalam Bahasa Indonesia dengan format:
NAMA_RUTINITAS: <nama yang menyala, tema juara/kesehatan>
PRODUK: <rekomendasi kombinasi dan dosis>
JADWAL: <detail waktu dan aturan minum harian>
CATATAN: <panduan aman, batasan, dan tips>

Hindari klaim medis. Fokus ke daya tahan tubuh, energi, relaksasi, pencernaan, dan gaya hidup sehat.`;
      const ai = await env.AI.run("@cf/moonshotai/kimi-k2.6", { messages: [{ role: "user", content: prompt }] });
      const text = ai.choices[0].message.content;
      const routineName = (text.match(/NAMA_RUTINITAS:\s*(.+)/i)?.[1] || "Rutinitas Juara").trim();
      const productRec = (text.match(/PRODUK:\s*([\s\S]+?)(?=JADWAL:|$)/i)?.[1] || "").trim();
      const schedule = (text.match(/JADWAL:\s*([\s\S]+?)(?=CATATAN:|$)/i)?.[1] || "").trim();
      const notes = (text.match(/CATATAN:\s*([\s\S]+)/i)?.[1] || "").trim();
      await env.DB.prepare("INSERT INTO recommendations (name, roast, flavor, method, budget, blend_name, description, brew_guide) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
        .bind(name || "", goal, habit, caffeine, suplemen || "tidak", routineName, productRec, schedule).run();
      return new Response(JSON.stringify({ name: name || "Sahabat Juara", routine_name: routineName, product_recommendation: productRec, schedule, notes }), { headers: { "Content-Type": "application/json" } });
    }

    if (request.method === "POST" && path === "/api/chat") {
      const body = await request.json();
      const message = (body.message || "").trim();
      if (!message) {
        return new Response(JSON.stringify({ reply: "Mau tanya soal kopi apa nih?" }), { headers: { "Content-Type": "application/json" } });
      }
      const system = `Kamu adalah Asisten AI Kopi Juara. Tugas: jawab pertanyaan soal produk Kopi Juwara (3in1 Arabika Brazil + VCO + Ekstrak Yung Kien Ganoderma strain YK-01) dan Yun Kim B / Yung Kien Ganoderma (kapsul, dosis 4 kapsul/hari). Berikan informasi konsumsi yang aman dan edukatif. Ini bersifat suplemen/kesehatan umum, bukan obat. Jangan klaim menyembuhkan penyakit. Jika user bicara kondisi medis, anjurkan konsultasi dokter. Jawaban singkat padat, maksimal 4 kalimat, dalam bahasa Indonesia.`;
      const ai = await env.AI.run("@cf/moonshotai/kimi-k2.6", { messages: [{ role: "system", content: system }, { role: "user", content: message }] });
      const reply = ai.choices[0].message.content;
      await env.DB.prepare("INSERT INTO chat_messages (role, message) VALUES (?, ?), (?, ?)")
        .bind("user", message, "assistant", reply).run();
      return new Response(JSON.stringify({ reply }), { headers: { "Content-Type": "application/json" } });
    }

    if (request.method === "GET" && path === "/api/stats") {
      const recs = await env.DB.prepare("SELECT COUNT(*) as total FROM recommendations").first();
      return new Response(JSON.stringify({ recommendations: recs.total }), { headers: { "Content-Type": "application/json" } });
    }

    return new Response(JSON.stringify({ error: "Not Found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }
};
// ak:6fcbc2827cd46957
