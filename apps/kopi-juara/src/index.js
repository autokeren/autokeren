import { initDB } from "./db/queries.js";
import route from "./api/index.js";
import { renderHTML } from "./html/page.js";

export default {
  async fetch(request, env) {
    await initDB(env.DB);

    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return new Response(renderHTML(), { headers: { "Content-Type": "text/html" } });
    }

    const apiResponse = await route(request, env);
    if (apiResponse) {
      return apiResponse;
    }

    return new Response(JSON.stringify({ error: "Not Found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  },
};
// ak:b3a83d57f6330bc9
