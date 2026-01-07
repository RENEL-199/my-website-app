import sqlite3

# Connect to your database
conn = sqlite3.connect("database.db")
c = conn.cursor()

# Drop the table if it already exists (to avoid "table already exists" error)
c.execute("DROP TABLE IF EXISTS cart_items_temp")
conn.commit()

# Create the new table with user_id
c.execute("""
    CREATE TABLE cart_items_temp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        menu_item_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (menu_item_id) REFERENCES menu_items(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")
conn.commit()

# Copy data from old table to the new table, assigning a default user_id of 1
c.execute("""
    INSERT INTO cart_items_temp (id, user_id, menu_item_id, quantity)
    SELECT id, 1, menu_item_id, quantity  -- Assigning default user_id (1)
    FROM cart_items
""")
conn.commit()

# Drop the old cart_items table
c.execute("DROP TABLE cart_items")
conn.commit()

# Rename the new table to cart_items
c.execute("ALTER TABLE cart_items_temp RENAME TO cart_items")
conn.commit()

conn.close()

print("Database updated successfully!")
