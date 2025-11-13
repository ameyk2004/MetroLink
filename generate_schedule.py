import mysql.connector
from datetime import datetime, timedelta, time

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Amey1234",  # change if needed
    "database": "metro_ticketing"
}

# Train settings (you can adjust)
START_TIME = time(6, 0)      # 06:00 AM
END_TIME = time(23, 0)       # 11:00 PM
FREQUENCY_MIN = 5            # Train every 5 minutes
TRAVEL_MIN = 2               # 2 minutes between stops
DWELL_SEC = 30               # 30 seconds at station


def connect():
    return mysql.connector.connect(**DB_CONFIG)


def fetch_lines_and_stops(conn):
    cur = conn.cursor(dictionary=True)

    # Fetch lines
    cur.execute("SELECT * FROM metro_lines ORDER BY line_id")
    lines = cur.fetchall()

    result = []
    for line in lines:
        line_id = line["line_id"]

        # Fetch stops in correct order
        cur.execute("""
            SELECT stop_id, stop_name, stop_order
            FROM stops
            WHERE line_id=%s
            ORDER BY stop_order ASC
        """, (line_id,))
        stops_up = cur.fetchall()

        stops_down = list(reversed(stops_up))

        result.append({
            "line_id": line_id,
            "line_name": line["line_name"],
            "stops_up": stops_up,
            "stops_down": stops_down
        })

    cur.close()
    return result


def insert_schedule_for_line(conn, line):
    cursor = conn.cursor()

    base_date = datetime(2025, 1, 1)  # dummy date for time-only

    start_dt = datetime.combine(base_date, START_TIME)
    end_dt = datetime.combine(base_date, END_TIME)
    current = start_dt

    total_inserted = 0

    print(f"→ Generating schedule for line: {line['line_name']}")

    while current <= end_dt:

        # -------------------------
        # UP Direction (start → end)
        # -------------------------
        depart = current
        for stop in line["stops_up"]:
            arr = depart
            dep = arr + timedelta(seconds=DWELL_SEC)

            cursor.execute("""
                INSERT INTO train_schedule (line_id, stop_id, arrival_time, departure_time, direction)
                VALUES (%s, %s, %s, %s, 'UP')
            """, (
                line['line_id'],
                stop['stop_id'],
                arr.time().replace(microsecond=0),
                dep.time().replace(microsecond=0)
            ))

            depart += timedelta(minutes=TRAVEL_MIN)
            total_inserted += 1

        # -------------------------
        # DOWN Direction (end → start)
        # -------------------------
        depart = current
        for stop in line["stops_down"]:
            arr = depart
            dep = arr + timedelta(seconds=DWELL_SEC)

            cursor.execute("""
                INSERT INTO train_schedule (line_id, stop_id, arrival_time, departure_time, direction)
                VALUES (%s, %s, %s, %s, 'DOWN')
            """, (
                line['line_id'],
                stop['stop_id'],
                arr.time().replace(microsecond=0),
                dep.time().replace(microsecond=0)
            ))

            depart += timedelta(minutes=TRAVEL_MIN)
            total_inserted += 1

        # Next train in 5 minutes
        current += timedelta(minutes=FREQUENCY_MIN)

    return total_inserted


def main():
    conn = connect()

    try:
        # Clear previous schedule
        cur = conn.cursor()
        cur.execute("DELETE FROM train_schedule")
        conn.commit()
        cur.close()

        print("✔ Previous schedule cleared")

        # Fetch lines & stops
        lines = fetch_lines_and_stops(conn)
        if not lines:
            print("ERROR: No lines found. Run setup.sql first.")
            return

        total_all = 0

        for line in lines:
            inserted = insert_schedule_for_line(conn, line)
            print(f"   Inserted {inserted} rows")
            total_all += inserted

        conn.commit()
        print(f"\n🎉 Schedule Generated Successfully!")
        print(f"Total rows inserted: {total_all}\n")

    except Exception as e:
        print("ERROR:", e)
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
