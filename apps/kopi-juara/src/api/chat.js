import { CHAT_SYSTEM_PROMPT } from "../config/prompts.js";
import { saveChatMessage } from "../db/queries.js";

const AI_MODEL = "@cf/moonshotai/kimi-k2.6";

export async function handleChat(request, env) {
  const body = await request.json();
  const message = (body.message || "").trim();

  if (!message) {
    return jsonResponse({ reply: "Mau tanya soal kopi apa nih?" });
  }

  const ai = await env.AI.run(AI_MODEL, {
    messages: [
      { role: "system", content: CHAT_SYSTEM_PROMPT },
      { role: "user", content: message },
    ],
  });

  const reply = ai.choices[0].message.content;
  await saveChatMessage(env.DB, "user", message);
  await saveChatMessage(env.DB, "assistant", reply);

  return jsonResponse({ reply });
}

function jsonResponse(data) {
  return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
}
// ak:74236acfa392f24e
