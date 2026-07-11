import { styles } from "./styles.js";
import { clientScript } from "./script.js";

export function renderHTML() {
  return `<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kopi Juara AI — Ciptakan Rutinitas Juaramu</title>
  <style>${styles}</style>
</head>
<body>
  <nav class="navbar">
    <div class="container nav-inner">
      <a class="logo" href="#">☕ Kopi Juara</a>
      <div class="nav-links">
        <a href="#fitur">Fitur</a>
        <a href="#ai-routine">AI Rutinitas</a>
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
          <div class="icon">🧠</div>
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

  <script>${clientScript}</script>
</body>
</html>`;
}
// ak:3d6f817f116a5f97
