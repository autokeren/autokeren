export const styles = `
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
`;
// ak:66be9aab5717c015
