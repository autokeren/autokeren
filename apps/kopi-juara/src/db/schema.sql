CREATE TABLE IF NOT EXISTS recommendations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  goal TEXT,
  habit TEXT,
  caffeine TEXT,
  suplemen TEXT,
  routine_name TEXT,
  product_recommendation TEXT,
  schedule TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role TEXT,
  message TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
# ak:a141bc515dcc13ec
