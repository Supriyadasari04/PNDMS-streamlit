import sqlite3

conn = sqlite3.connect("users.db")  # Replace with actual DB name
c = conn.cursor()

c.execute("PRAGMA table_info(users)")
columns = c.fetchall()

print("Users table columns:")
for col in columns:
    print(f"{col[1]} ({col[2]})")
