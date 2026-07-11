import schemaSql from "./schema.sql" with { type: "text" };

export async function initDB(db) {
  for (const statement of schemaSql.split(";").map((s) => s.trim()).filter(Boolean)) {
    await db.prepare(statement + ";").run();
  }
}

export async function saveRecommendation(db, data) {
  const {
    name = "",
    goal = "",
    habit = "",
    caffeine = "",
    suplemen = "tidak",
    routineName = "Rutinitas Juara",
    productRecommendation = "",
    schedule = "",
  } = data;

  await db
    .prepare(
      `INSERT INTO recommendations
       (name, goal, habit, caffeine, suplemen, routine_name, product_recommendation, schedule)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(name, goal, habit, caffeine, suplemen, routineName, productRecommendation, schedule)
    .run();
}

export async function saveChatMessage(db, role, message) {
  await db.prepare("INSERT INTO chat_messages (role, message) VALUES (?, ?)").bind(role, message).run();
}

export async function countRecommendations(db) {
  const row = await db.prepare("SELECT COUNT(*) as total FROM recommendations").first();
  return row?.total ?? 0;
}
// ak:d8b41593df41595e
