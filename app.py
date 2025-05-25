import os
import json
import gspread
import psycopg2
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import tempfile
from datetime import datetime

# Assuming your timestamp format is 'DD/MM/YYYY HH:MM:SS'
timestamp_format = "%d/%m/%Y %H:%M:%S"

load_dotenv()  # Load env vars from .env

# Environment variables
SHEET_NAME = os.getenv('SHEET_NAME')
DB_CONFIG = os.getenv('POSTGRES_URI')

# Load credentials from environment variable
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')
if not GOOGLE_CREDENTIALS:
    raise ValueError("GOOGLE_CREDENTIALS environment variable is missing.")

# Parse the JSON string to a dictionary
credentials_dict = json.loads(GOOGLE_CREDENTIALS)

# Google Sheets auth
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)


headers = ['Timestamp', 'Date', 'Time', 'Nappy', 'Email Address']
spreadsheet = client.open(SHEET_NAME)
worksheet = spreadsheet.worksheet('Form Responses 1')  # or the tab you want
rows = worksheet.get_all_records(expected_headers=headers)

if not rows:
    print("No data found in sheet.")
    exit()

# Connect to Postgres
conn = psycopg2.connect(DB_CONFIG)
cursor = conn.cursor()

# Get latest timestamp from DB
cursor.execute("""
    SELECT *
    FROM nappy_log
    WHERE timestamp = (SELECT Max(timestamp) FROM nappy_log);
""")
last_timestamp = cursor.fetchone()[0]
print(last_timestamp)

# Convert last_timestamp from DB to datetime if it's not None and it's a string
if last_timestamp and isinstance(last_timestamp, str):
    last_timestamp = datetime.strptime(last_timestamp, timestamp_format)

# Filter rows with parsed timestamps
new_rows = []
for row in rows:
    ts_str = row['Timestamp']
    if not ts_str:
        # Skip rows with empty Timestamp
        continue
    
    try:
        row_ts = datetime.strptime(ts_str, timestamp_format)
    except ValueError:
        print(f"Skipping row with invalid timestamp: {ts_str}")
        continue

    if not last_timestamp or row_ts > last_timestamp:
        new_rows.append(row)


print(new_rows)

if new_rows:
    latest = new_rows[-1]  # Insert only the most recent new row
    latest_ts = datetime.strptime(latest['Timestamp'], timestamp_format)

    cursor.execute("""
        INSERT INTO nappy_log (timestamp, date, time, nappy, email_address)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (timestamp) DO NOTHING;
    """, (
        latest_ts,
        latest['Date'],
        latest['Time'],
        latest['Nappy'],
        latest['Email Address']
    ))
    conn.commit()
    print(f"Inserted new row with timestamp: {latest['Timestamp']}")
else:
    print("No new rows found since last run.")

cursor.close()
conn.close()