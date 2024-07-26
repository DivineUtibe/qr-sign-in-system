CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT,
    time_logged TEXT  -- Using TEXT type to store timestamps
);

CREATE TABLE IF NOT EXISTS sign_ins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,       -- Added email column
    date TEXT NOT NULL,
    time TEXT NOT NULL
);
