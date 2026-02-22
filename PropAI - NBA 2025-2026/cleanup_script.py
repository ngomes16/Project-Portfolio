import sqlite3
import os

DB_PATH = "data/db/nba_props.sqlite3"

def clean_data():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Cleaning up test data for 2026-01-04...")
        
        # 1. Remove picks generated for that date
        cursor.execute("DELETE FROM model_picks WHERE pick_date = '2026-01-04'")
        print(f"Removed model picks for 01/04/2026.")

        # 2. Remove scheduled LAL/BOS game or any game on that date involving those teams
        # Using a subquery approach to be safe with team names if IDs vary, or just date/team criteria
        # Assuming teams table exists and matches names roughly
        cursor.execute("""
            DELETE FROM scheduled_games 
            WHERE game_date = '2026-01-04' 
            AND (
                away_team_id IN (SELECT id FROM teams WHERE name LIKE '%Lakers%' OR name LIKE '%Celtics%') OR
                home_team_id IN (SELECT id FROM teams WHERE name LIKE '%Lakers%' OR name LIKE '%Celtics%')
            )
        """)
        
        # Also try to clean up if they were inserted into 'games' for testing
        cursor.execute("""
            DELETE FROM games 
            WHERE game_date = '2026-01-04'
            AND (
                team1_id IN (SELECT id FROM teams WHERE name LIKE '%Lakers%' OR name LIKE '%Celtics%') OR
                team2_id IN (SELECT id FROM teams WHERE name LIKE '%Lakers%' OR name LIKE '%Celtics%')
            )
        """)
        
        print(f"Removed LAL/BOS games for 01/04/2026.")
        
        conn.commit()
        print("Cleanup successful.")
        
    except Exception as e:
        print(f"Error cleaning data: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clean_data()
