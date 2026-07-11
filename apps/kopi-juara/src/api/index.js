import { handleRecommend } from "./recommend.js";
import { handleChat } from "./chat.js";
import { handleStats } from "./stats.js";

const routes = new Map([
  ["/api/recommend", { method: "POST", handler: handleRecommend }],
  ["/api/chat", { method: "POST", handler: handleChat }],
  ["/api/stats", { method: "GET", handler: handleStats }],
]);

export default async function route(request, env) {
  const { pathname } = new URL(request.url);
  const config = routes.get(pathname);

  if (config && request.method === config.method) {
    try {
      return await config.handler(request, env);
    } catch (error) {
      console.error(`API error on ${pathname}:`, error);
      return jsonError("Terjadi kesalahan server", 500);
    }
  }

  return null;
}

function jsonError(message, status) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
// ak:086696fce44c0b26
