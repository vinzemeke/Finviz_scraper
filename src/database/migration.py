import sqlite3

class MigrationManager:
    def __init__(self, db_path='data/finviz_scraper.db'):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def run_migrations(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # Migration for watchlists table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    user_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Migration: Created 'watchlists' table.")
        except sqlite3.OperationalError as e:
            print(f"Migration Error creating 'watchlists' table: {e}")

        # Migration for watchlist_tickers table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist_tickers (
                    watchlist_id INTEGER NOT NULL,
                    ticker_symbol TEXT NOT NULL,
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (watchlist_id, ticker_symbol),
                    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
                )
            """)
            print("Migration: Created 'watchlist_tickers' table.")
        except sqlite3.OperationalError as e:
            print(f"Migration Error creating 'watchlist_tickers' table: {e}")

        # Migration for simulation_results table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    option_symbol TEXT NOT NULL,
                    simulation_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Migration: Created 'simulation_results' table.")
        except sqlite3.OperationalError as e:
            print(f"Migration Error creating 'simulation_results' table: {e}")

        # Migration for user_preferences table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    underpricing_threshold REAL DEFAULT 0.05,
                    strike_range REAL DEFAULT 0.10,
                    other_settings TEXT
                )
            """)
            print("Migration: Created 'user_preferences' table.")
        except sqlite3.OperationalError as e:
            print(f"Migration Error creating 'user_preferences' table: {e}")

        # Add indexes to simulation_results
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_simulation_results_ticker
                ON simulation_results (ticker);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_simulation_results_option_symbol
                ON simulation_results (option_symbol);
            """)
            print("Migration: Added indexes to 'simulation_results' table.")
        except sqlite3.OperationalError as e:
            print(f"Migration Error adding indexes to 'simulation_results' table: {e}")

        # Migration for adding last_scraped column to urls table (if not exists)
        try:
            cursor.execute("ALTER TABLE urls ADD COLUMN last_scraped DATETIME")
            print("Migration: Added 'last_scraped' column to 'urls' table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Migration: 'last_scraped' column already exists. Skipping.")
            else:
                raise e

        # Migration for adding volume and 52-week range columns to ticker_properties table
        try:
            cursor.execute("ALTER TABLE ticker_properties ADD COLUMN volume REAL")
            print("Migration: Added 'volume' column to 'ticker_properties' table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Migration: 'volume' column already exists. Skipping.")
            else:
                raise e

        try:
            cursor.execute("ALTER TABLE ticker_properties ADD COLUMN fifty_two_week_high REAL")
            print("Migration: Added 'fifty_two_week_high' column to 'ticker_properties' table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Migration: 'fifty_two_week_high' column already exists. Skipping.")
            else:
                raise e

        try:
            cursor.execute("ALTER TABLE ticker_properties ADD COLUMN fifty_two_week_low REAL")
            print("Migration: Added 'fifty_two_week_low' column to 'ticker_properties' table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Migration: 'fifty_two_week_low' column already exists. Skipping.")
            else:
                raise e

        try:
            cursor.execute("ALTER TABLE ticker_properties ADD COLUMN fifty_two_week_range TEXT")
            print("Migration: Added 'fifty_two_week_range' column to 'ticker_properties' table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Migration: 'fifty_two_week_range' column already exists. Skipping.")
            else:
                raise e

        conn.commit()
        conn.close()

    def rollback_migrations(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # Drop tables in reverse order of creation due to foreign key dependencies
        try:
            cursor.execute("DROP TABLE IF EXISTS user_preferences")
            print("Rollback: Dropped 'user_preferences' table.")
        except sqlite3.OperationalError as e:
            print(f"Rollback Error dropping 'user_preferences' table: {e}")

        try:
            cursor.execute("DROP TABLE IF EXISTS simulation_results")
            print("Rollback: Dropped 'simulation_results' table.")
        except sqlite3.OperationalError as e:
            print(f"Rollback Error dropping 'simulation_results' table: {e}")

        try:
            cursor.execute("DROP TABLE IF EXISTS watchlist_tickers")
            print("Rollback: Dropped 'watchlist_tickers' table.")
        except sqlite3.OperationalError as e:
            print(f"Rollback Error dropping 'watchlist_tickers' table: {e}")

        try:
            cursor.execute("DROP TABLE IF EXISTS watchlists")
            print("Rollback: Dropped 'watchlists' table.")
        except sqlite3.OperationalError as e:
            print(f"Rollback Error dropping 'watchlists' table: {e}")

        conn.commit()
        conn.close()

if __name__ == '__main__':
    # This block is for testing the migration directly
    migration_manager = MigrationManager()
    migration_manager.run_migrations()
