import sqlite3

# Connect to your database
conn = sqlite3.connect("database.db")
c = conn.cursor()

# Delete all rows from menu_items
c.execute("DELETE FROM menu_items")


conn.commit()
conn.close()

print("All menu items have been deleted!")

