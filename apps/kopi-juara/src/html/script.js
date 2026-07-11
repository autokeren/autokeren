export const clientScript = `
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
  nextBtn.textContent = currentStep === totalSteps ? 'Temukan Rutinitas' : 'Selanjutnya';
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
`;
// ak:57af1fac96f3240f
