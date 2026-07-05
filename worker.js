const htmlContent = `<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Servis HP Ceria - Solusi Handphone & Tablet Anda</title>
  <meta name="description" content="Servis HP Ceria melayani perbaikan handphone, ganti LCD, baterai, dan perbaikan chipset. Bergaransi, fast service, whatsapp 0812-3456-7890." />
  <meta property="og:title" content="Servis HP Ceria" />
  <meta property="og:description" content="Service handphone terpercaya, bergaransi, fast service." />
  <style>
    :root {
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --secondary: #0ea5e9;
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #1e293b;
      --muted: #64748b;
      --accent: #f59e0b;
      --success: #10b981;
      --shadow: 0 10px 40px rgba(30,41,59,0.12);
      --radius: 18px;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }
    a { color: inherit; text-decoration: none; }
    .container { width: min(1120px, 92%); margin: 0 auto; }
    header {
      position: fixed; inset: 0 0 auto 0; z-index: 50;
      background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(226,232,240,0.8);
    }
    nav { display: flex; align-items: center; justify-content: space-between; height: 70px; }
    .logo { font-weight: 800; font-size: 1.35rem; color: var(--primary); display: flex; align-items: center; gap: 0.5rem; }
    .logo svg { width: 32px; height: 32px; }
    .nav-links { display: flex; gap: 2rem; font-weight: 600; font-size: 0.95rem; }
    .nav-links a:hover { color: var(--primary); }
    .btn {
      display: inline-flex; align-items: center; gap: 0.5rem;
      padding: 0.85rem 1.6rem; border-radius: 999px; font-weight: 700;
      transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
      cursor: pointer; border: none;
    }
    .btn:hover { transform: translateY(-2px); }
    .btn-primary { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: #fff; box-shadow: 0 8px 20px rgba(37,99,235,0.35); }
    .btn-primary:hover { box-shadow: 0 10px 28px rgba(37,99,235,0.45); }
    .btn-whatsapp { background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; box-shadow: 0 8px 20px rgba(34,197,94,0.3); }
    .btn-outline { border: 2px solid var(--primary); color: var(--primary); background: #fff; }
    .mobile-menu { display: none; background: none; border: none; cursor: pointer; }
    @media (max-width: 760px) {
      .nav-links { display: none; position: absolute; top: 70px; left: 0; right: 0; background: #fff; flex-direction: column; padding: 1.5rem; gap: 1.25rem; border-bottom: 1px solid #e2e8f0; box-shadow: var(--shadow); }
      .nav-links.open { display: flex; }
      .mobile-menu { display: block; }
    }
    .hero {
      padding: 150px 0 100px; position: relative; overflow: hidden;
      background: radial-gradient(circle at 85% 10%, rgba(14,165,233,0.12), transparent 35%), radial-gradient(circle at 10% 80%, rgba(37,99,235,0.10), transparent 35%), var(--bg);
    }
    .hero-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 4rem; align-items: center; }
    .hero h1 { font-size: clamp(2.2rem, 5vw, 3.6rem); line-height: 1.15; font-weight: 900; letter-spacing: -0.03em; }
    .hero h1 span { background: linear-gradient(135deg, var(--primary), var(--secondary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { font-size: 1.15rem; color: var(--muted); margin: 1.5rem 0 2rem; max-width: 520px; }
    .hero-badges { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem; }
    .badge { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.45rem 0.95rem; border-radius: 999px; background: #fff; border: 1px solid #e2e8f0; font-size: 0.85rem; font-weight: 600; color: var(--muted); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .hero-graphic { position: relative; display: flex; justify-content: center; align-items: center; }
    .phone-mockup {
      width: 260px; height: 500px; border-radius: 40px; background: linear-gradient(145deg, #1e293b, #0f172a);
      box-shadow: var(--shadow), inset 0 0 0 6px #334155; position: relative; transform: rotate(-6deg);
      display: flex; align-items: center; justify-content: center;
    }
    .phone-mockup::before { content: ""; position: absolute; top: 18px; width: 80px; height: 20px; background: #334155; border-radius: 12px; }
    .phone-screen { width: 92%; height: 86%; margin-top: 28px; border-radius: 28px; background: linear-gradient(135deg, #dbeafe, #eff6ff); border: 1px solid #bfdbfe; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; color: var(--primary); font-weight: 800; text-align: center; padding: 1.5rem; }
    .phone-screen svg { width: 80px; height: 80px; opacity: 0.9; }
    .hero-float-card {
      position: absolute; background: #fff; padding: 1rem 1.2rem; border-radius: var(--radius); box-shadow: var(--shadow); display: flex; align-items: center; gap: 0.75rem; font-weight: 700; font-size: 0.95rem; animation: float 5s ease-in-out infinite;
    }
    .hero-float-card.one { bottom: 55px; left: 0; animation-delay: 0s; }
    .hero-float-card.two { top: 40px; right: 0; animation-delay: 2.5s; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--success); }
    @keyframes float { 0%,100% {transform: translateY(0);} 50% {transform: translateY(-10px);} }
    @media (max-width: 900px) {
      .hero-grid { grid-template-columns: 1fr; text-align: center; }
      .hero p { margin-left: auto; margin-right: auto; }
      .hero-badges { justify-content: center; }
      .hero-graphic { order: -1; }
      .phone-mockup { transform: rotate(0deg) scale(0.9); }
      .hero-float-card { display: none; }
    }
    section { padding: 90px 0; }
    .section-title { text-align: center; max-width: 620px; margin: 0 auto 3.5rem; }
    .section-label { text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.8rem; font-weight: 800; color: var(--primary); margin-bottom: 0.5rem; }
    .section-title h2 { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 900; line-height: 1.2; margin-bottom: 0.75rem; }
    .section-title p { color: var(--muted); font-size: 1.05rem; }
    .services-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem; }
    .service-card { background: var(--card); border-radius: var(--radius); padding: 2rem; box-shadow: var(--shadow); transition: transform 0.25s ease, box-shadow 0.25s ease; border: 1px solid #e2e8f0; }
    .service-card:hover { transform: translateY(-6px); box-shadow: 0 20px 50px rgba(30,41,59,0.16); }
    .service-icon { width: 56px; height: 56px; border-radius: 16px; display: flex; align-items: center; justify-content: center; margin-bottom: 1.25rem; font-size: 1.6rem; }
    .service-card h3 { font-size: 1.2rem; font-weight: 800; margin-bottom: 0.6rem; }
    .service-card p { color: var(--muted); font-size: 0.95rem; }
    .pricing { background: #fff; }
    .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.75rem; }
    .pricing-card { background: var(--bg); border-radius: var(--radius); padding: 2rem; border: 2px solid transparent; transition: all 0.25s ease; position: relative; }
    .pricing-card:hover { border-color: var(--primary); transform: translateY(-5px); }
    .pricing-card.popular { background: linear-gradient(180deg, #eff6ff, #fff); border-color: var(--primary); }
    .popular-tag { position: absolute; top: -14px; right: 20px; background: var(--accent); color: #fff; padding: 0.35rem 0.9rem; border-radius: 999px; font-weight: 800; font-size: 0.75rem; }
    .pricing-card h3 { font-size: 1.25rem; font-weight: 800; margin-bottom: 0.5rem; }
    .price { font-size: 2.2rem; font-weight: 900; color: var(--primary); margin: 0.75rem 0; }
    .price span { font-size: 0.95rem; font-weight: 600; color: var(--muted); }
    .pricing-card ul { list-style: none; margin: 1.25rem 0; }
    .pricing-card li { display: flex; align-items: flex-start; gap: 0.6rem; padding: 0.45rem 0; color: var(--text); font-size: 0.95rem; }
    .pricing-card li::before { content: "✓"; color: var(--success); font-weight: 800; }
    .location { background: linear-gradient(180deg, #f8fafc, #eff6ff); }
    .location-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2.5rem; align-items: center; }
    .map-frame { background: #fff; border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow); border: 1px solid #e2e8f0; height: 340px; }
    .map-frame iframe { width: 100%; height: 100%; border: 0; }
    .info-list { display: flex; flex-direction: column; gap: 1.25rem; }
    .info-item { background: #fff; border-radius: var(--radius); padding: 1.3rem 1.5rem; box-shadow: var(--shadow); border: 1px solid #e2e8f0; display: flex; align-items: flex-start; gap: 1rem; }
    .info-icon { width: 44px; height: 44px; border-radius: 12px; background: #eff6ff; color: var(--primary); display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1.25rem; }
    .info-item h4 { font-weight: 800; margin-bottom: 0.25rem; }
    .info-item p { color: var(--muted); font-size: 0.95rem; }
    @media (max-width: 800px) {
      .location-grid { grid-template-columns: 1fr; }
      .map-frame { height: 280px; }
    }
    .contact { background: #fff; text-align: center; }
    .contact-box { max-width: 680px; margin: 0 auto; background: linear-gradient(135deg, var(--primary), var(--secondary)); border-radius: var(--radius); padding: 3rem 2rem; color: #fff; box-shadow: var(--shadow); }
    .contact-box h2 { font-size: 2rem; font-weight: 900; margin-bottom: 0.75rem; }
    .contact-box p { opacity: 0.95; font-size: 1.05rem; margin-bottom: 1.75rem; }
    .wa-btn { display: inline-flex; align-items: center; gap: 0.6rem; background: #fff; color: var(--primary); padding: 1rem 2rem; border-radius: 999px; font-weight: 800; font-size: 1.1rem; box-shadow: 0 10px 28px rgba(0,0,0,0.18); transition: transform 0.2s ease; }
    .wa-btn:hover { transform: scale(1.03); }
    footer { background: #0f172a; color: #cbd5e1; padding: 50px 0 25px; }
    .footer-grid { display: grid; grid-template-columns: 1.5fr 1fr 1fr; gap: 2.5rem; margin-bottom: 2.5rem; }
    footer h4 { color: #fff; font-weight: 800; margin-bottom: 1rem; }
    footer a { color: #94a3b8; display: block; margin: 0.4rem 0; transition: color 0.2s ease; }
    footer a:hover { color: #fff; }
    .footer-bottom { border-top: 1px solid #1e293b; padding-top: 1.5rem; text-align: center; font-size: 0.9rem; color: #64748b; }
    @media (max-width: 760px) {
      .footer-grid { grid-template-columns: 1fr; gap: 2rem; }
    }
    .toast {
      position: fixed; bottom: 24px; right: 24px; background: #0f172a; color: #fff; padding: 1rem 1.5rem; border-radius: 12px; box-shadow: var(--shadow); font-weight: 600; transform: translateY(120px); opacity: 0; transition: all 0.35s ease; z-index: 100;
    }
    .toast.show { transform: translateY(0); opacity: 1; }
  </style>
</head>
<body>
  <header>
    <nav class="container">
      <a href="#" class="logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="3"/><path d="M12 18h.01"/></svg>
        Servis      <button class="mobile-menu" aria-label="Menu" aria-expanded="false" onclick="document.querySelector('.nav-links').classList.toggle('open'); this.setAttribute('aria-expanded', document.querySelector('.nav-links').classList.contains('open'));">
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>
      <div class="nav-links">
        <a href="#layanan">Layanan</a>
        <a href="#harga">Harga</a>
        <a href="#lokasi">Lokasi</a>
        <a href="#kontak">Kontak</a>
      </div>
    </nav>
  </header>

  <section class="hero" id="beranda">
    <div class="container hero-grid">
      <div>
        <div class="hero-badges">
          <span class="badge">⚡ Fast Service</span>
          <span class="badge">🛡️ Garansi 90 Hari</span>
          <span class="badge">✅ Teknisi Berpengalaman</span>
        </div>
        <h1>Perbaikan Handphone <span>Cepat & Bergaransi</span></h1>
        <p>Servis HP Ceria siap membantu perbaikan LCD, baterai, chipset, water damage, dan berbagai masalah smartphone & tablet Anda. Hasil rapi, harga transparan.</p>
        <div class="hero-cta">
          <a href="#kontak" class="btn btn-primary">Konsultasi Gratis</a>
          <a href="#harga" class="btn btn-outline">Lihat Harga</a>
        </div>
      </div>
      <div class="hero-graphic">
        <div class="phone-mockup">
          <div class="phone-screen">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 18h.01"/><path d="M12 2a4 4 0 014 4c0 2.5-3 2.5-3 5"/><circle cx="12" cy="19" r="1"/></svg>
            <div>HP Rusak?<br/>Kami Siap Memperbaiki</div>
          </div>
        </div>
        <div class="hero-float-card one"><span class="dot"></span> Teknisi Ahli</div>
        <div class="hero-float-card two">🕒 Buka Setiap Hari</div>
      </div>
    </div>
  </section>

  <section id="layanan">
    <div class="container">
      <div class="section-title">
        <p class="section-label">Layanan Kami</p>
        <h2>Solusi Lengkap untuk HP & Tablet Anda</h2>
        <p>Menggunakan suku cadang berkualitas dan proses perbaikan yang teliti.</p>
      </div>
      <div class="services-grid">
        <div class="service-card">
          <div class="service-icon" style="background:#eff6ff">📱</div>
          <h3>Ganti LCD & Touchscreen</h3>
          <p>LCD pecah, retak, ghost touch, atau tidak responsif? Kami ganti dengan panel berkualitas agar tampilan kembali jernih.</p>
        </div>
        <div class="service-card">
          <div class="service-icon" style="background:#ecfdf5">🔋</div>
          <h3>Ganti Baterai</h3>
          <p>Baterai boros, kembung, atau cepat panas? Ganti baterai original agar HP kembali awet seharian.</p>
        </div>
        <div class="service-card">
          <div class="service-icon" style="background:#fff7ed">🔌</div>
          <h3>Perbaikan Cas & IC Power</h3>
          <p>HP tidak ngecas, sering restart, atau mati total? Servis IC power, konektor cas, dan jalur listrik terjamin aman.</p>
        </div>
        <div class="service-card">
          <div class="service-icon" style="background:#fef2f2">💧</div>
          <h3>Water Damage</h3>
          <p>Terkena air atau tumpahan minuman? Bawa segera untuk cleaning dan pencegahan korosi pada komponen penting.</p>
        </div>
        <div class="service-card">
          <div class="service-icon" style="background:#faf5ff">🧠</div>
          <h3>Perbaikan Chipset/CPU</h3>
          <p>HP bootloop, hang logo, atau panas berlebihan? Layanan reballing dan perbaikan chipset oleh teknisi berpengalaman.</p>
        </div>
        <div class="service-card">
          <div class="service-icon" style="background:#f0fdfa">🔊</div>
          <h3>Speaker, Kamera & Tombol</h3>
          <p>Suara pecah, kamera buram, tombol tidak berfungsi? Kami perbaiki modul kecil dengan harga terjangkau.</p>
        </div>
      </div>
    </div>
  </section>

  <section class="pricing" id="harga">
    <div class="container">
      <div class="section-title">
        <p class="section-label">Daftar Harga</p>
        <h2>Harga Transparan, Tanpa Biaya Tersembunyi</h2>
        <p>Harga bisa berbeda tergantung model HP dan tingkat kerusakan. Konsultasi gratis untuk estimasi akurat.</p>
      </div>
      <div class="pricing-grid">
        <div class="pricing-card">
          <h3>Service Ringan</h3>
          <p style="color:var(--muted);font-size:.95rem">Tombol, speaker, kamera, konektor</p>
          <div class="price">Rp 150rb <span>mulai</span></div>
          <ul>
            <li>Pemeriksaan gratis</li>
            <li>Ganti komponen sesuai kerusakan</li>
            <li>Garansi sparepart 30 hari</li>
            <li>Estimasi 30 - 60 menit</li>
          </ul>
          <a href="#kontak" class="btn btn-outline" style="width:100%;justify-content:center;">Pesan Sekarang</a>
        </div>
        <div class="pricing-card popular">
          <span class="popular-tag">PALING LARIS</span>
          <h3>Ganti LCD / Baterai</h3>
          <p style="color:var(--muted);font-size:.95rem">Semua merek & model</p>
          <div class="price">Rp 350rb <span>mulai</span></div>
          <ul>
            <li>Suku cadang berkualitas</li>
            <li>Garansi 90 hari</li>
            <li>Pasang rapi & presisi</li>
            <li>Estimasi 1 - 2 jam</li>
          </ul>
          <a href="#kontak" class="btn btn-primary" style="width:100%;justify-content:center;">Pesan Sekarang</a>
        </div>
        <div class="pricing-card">
          <h3>Perbaikan Mesin</h3>
          <p style="color:var(--muted);font-size:.95rem">IC power, cas, CPU, water damage</p>
          <div class="price">Rp 500rb <span>mulai</span></div>
          <ul>
            <li>Diagnosa detail</li>
            <li>Perbaikan di tingkat chipset</li>
            <li>Garansi servis 30 hari</li>
            <li>Estimasi 1 - 3 hari</li>
          </ul>
          <a href="#kontak" class="btn btn-outline" style="width:100%;justify-content:center;">Pesan Sekarang</a>
        </div>
      </div>
    </div>
  </section>

  <section class="location" id="lokasi">
    <div class="container location-grid">
      <div class="map-frame">
        <iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3966.2874145229787!2d106.82715331537434!3d-6.230289595490216!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x2e69f3e5e70e6e9f%3A0x301f0!2sJakarta%20Selatan!5e0!3m2!1sid!2sid!4v1600000000000!5m2!1sid!2sid" allowfullscreen loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
      </div>
      <div class="info-list">
        <div class="section-title" style="text-align:left;margin:0 0 1rem 0;">
          <p class="section-label">Lokasi Kami</p>
          <h2>Kunjungi Bengkel Servis HP Ceria</h2>
        </div>
        <div class="info-item">
          <div class="info-icon">📍</div>
          <div>
            <h4>Alamat</h4>
            <p>Jl. Gatot Subroto Kav. 59A, Kuningan, Jakarta Selatan 12950<br/>Lantai 1, Ruko Tekno Center Blok C12</p>
          </div>
        </div>
        <div class="info-item">
          <div class="info-icon">🕒</div>
          <div>
            <h4>Jam Operasional</h4>
            <p>Senin - Sabtu: 09.00 - 20.00 WIB<br/>Minggu: 10.00 - 17.00 WIB</p>
          </div>
        </div>
        <div class="info-item">
          <div class="info-icon">📞</div>
          <div>
            <h4>Telepon / WhatsApp</h4>
            <p><a href="https://wa.me/6281234567890" target="_blank">0812-3456-7890</a></p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="contact" id="kontak">
    <div class="container">
      <div class="contact-box">
        <h2>Butuh Bantuan Sekarang?</h2>
        <p>Chat kami langsung via WhatsApp untuk konsultasi gratis, booking servis, atau tanya estimasi harga. Respon cepat!</p>
        <a href="https://wa.me/6281234567890?text=Halo%20Servis%20HP%20Ceria%2C%20saya%20mau%20tanya%20tentang%20servis%20HP." class="wa-btn" target="_blank" rel="noopener noreferrer" onclick="showToast()">
          💬 Chat WhatsApp
        </a>
        <p style="margin-top:1.25rem;font-size:.95rem;opacity:.9">Atau telepon: <strong>0812-3456-7890</strong></p>
      </div>
    </div>
  </section>

  <footer>
    <div class="container">
      <div class="footer-grid">
        <div>
          <a href="#" class="logo" style="margin-bottom:.75rem">Servis HP Ceria</a>
          <p style="color:#94a3b8;font-size:.95rem;max-width:310px;">Solusi terpercaya untuk perbaikan handphone dan tablet. Melayani dengan profesional, jujur, dan bergaransi.</p>
        </div>
        <div>
          <h4>Menu</h4>
          <a href="#layanan">Layanan</a>
          <a href="#harga">Harga</a>
          <a href="#lokasi">Lokasi</a>
          <a href="#kontak">Kontak</a>
        </div>
        <div>
          <h4>Hubungi Kami</h4>
          <a href="https://wa.me/6281234567890" target="_blank">WhatsApp</a>
          <a href="tel:+6281234567890">0812-3456-7890</a>
          <a href="mailto:info@servishp ceria.id">info@servishpceria.id</a>
        </div>
      </div>
      <div class="footer-bottom">
        © 2026 Servis HP Ceria. All rights reserved.
      </div>
    </div>
  </footer>

  <div class="toast" id="toast">📲 Menuju WhatsApp...</div>
  <script>
    function showToast() {
      const toast = document.getElementById('toast');
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2500);
    }
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function (e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          document.querySelector('.nav-links').classList.remove('open');
        }
      });
    });
  </script>
</body>
</html>`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/health") {
      return new Response(JSON.stringify({ ok: true, service: "Servis HP Ceria" }), {
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(htmlContent, {
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  },
};
