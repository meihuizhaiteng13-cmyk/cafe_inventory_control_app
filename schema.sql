PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS stock_moves;
DROP TABLE IF EXISTS item_delete_history;
DROP TABLE IF EXISTS items;

CREATE TABLE items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  qty INTEGER NOT NULL DEFAULT 0,
  unit TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  is_deleted INTEGER NOT NULL DEFAULT 0 CHECK(is_deleted IN (0,1)),
  deleted_at TEXT
);

CREATE TABLE item_delete_history (
  history_id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  qty INTEGER NOT NULL,
  unit TEXT NOT NULL,
  deleted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE stock_moves (
  move_id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL,
  direction TEXT NOT NULL CHECK(direction IN ('IN','OUT')),
  qty INTEGER NOT NULL,
  note TEXT,
  happened_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(item_id) REFERENCES items(id)
);
