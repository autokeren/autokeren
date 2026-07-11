import { buildRoutinePrompt } from "../config/prompts.js";
import { saveRecommendation } from "../db/queries.js";

const AI_MODEL = "@cf/moonshotai/kimi-k2.6";

export async function handleRecommend(request, env) {
  const body = await request.json();
  const { name, goal, habit, caffeine, suplemen } = body;

  if (!goal || !habit || !caffeine) {
    return jsonError("Semua pilihan harus diisi", 400);
  }

  const prompt = buildRoutinePrompt({ name, goal, habit, caffeine, suplemen });
  const ai = await env.AI.run(AI_MODEL, { messages: [{ role: "user", content: prompt }] });
  const text = ai.choices[0].message.content;

  const routineName = extractField(text, /NAMA_RUTINITAS:\s*(.+)/i) || "Rutinitas Juara";
  const productRec = extractBlock(text, /PRODUK:\s*([\s\S]+?)(?=JADWAL:|$)/i);
  const schedule = extractBlock(text, /JADWAL:\s*([\s\S]+?)(?=CATATAN:|$)/i);
  const notes = extractBlock(text, /CATATAN:\s*([\s\S]+)/i);

  await saveRecommendation(env.DB, {
    name: name || "",
    goal,
    habit,
    caffeine,
    suplemen: suplemen || "tidak",
    routineName,
    productRecommendation: productRec,
    schedule,
  });

  return jsonResponse({
    name: name || "Sahabat Juara",
    routine_name: routineName,
    product_recommendation: productRec,
    schedule,
    notes,
  });
}

function extractField(text, regex) {
  return (text.match(regex)?.[1] || "").trim();
}

function extractBlock(text, regex) {
  return (text.match(regex)?.[1] || "").trim();
}

function jsonResponse(data) {
  return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
}

function jsonError(message, status) {
  return new Response(JSON.stringify({ error: message }), { status, headers: { "Content-Type": "application/json" } });
}
// ak:38d5fd2e48d316df
