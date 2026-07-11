import { countRecommendations } from "../db/queries.js";

export async function handleStats(_request, env) {
  const total = await countRecommendations(env.DB);
  return new Response(JSON.stringify({ recommendations: total }), {
    headers: { "Content-Type": "application/json" },
  });
}
// ak:e670fa7eb89e4567
