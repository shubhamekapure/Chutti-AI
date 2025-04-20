from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
CALENDARIFIC_API_KEY = os.getenv("CALENDARIFIC_API_KEY")

# Check if API key is available
if not CALENDARIFIC_API_KEY:
    print("ERROR: Calendarific API key not found!")
    print("Please create a .env file in the project root with your API key:")
    print("CALENDARIFIC_API_KEY=your_api_key_here")
    print("You can get a free API key from https://calendarific.com/")
    sys.exit(1)

app = Flask(__name__)
CORS(app)

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def str_to_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

def date_to_str(d):
    return d.strftime("%Y-%m-%d")

def get_holidays(start_date, end_date, location):
    # Map common country names to codes
    COUNTRY_MAP = {
        # Asia
        "India": "IN",
        "China": "CN",
        "Pakistan": "PK",
        "Bangladesh": "BD",
        "Japan": "JP",
        "Singapore": "SG",
        "Indonesia": "ID",
        
        # North America
        "United States": "US",
        "USA": "US",
        "Canada": "CA",
        "Mexico": "MX",
        
        # Europe
        "United Kingdom": "GB",
        "UK": "GB",
        "France": "FR",
        "Germany": "DE",
        "Italy": "IT",
        "Spain": "ES"
    }
    
    # Get country from location, defaulting to IN if not provided
    country = location.get("country", "IN")
    # Map country name to code if needed
    country_code = COUNTRY_MAP.get(country, country)
    
    state = location.get("state")
    holidays = []
    
    # Construct API URL with country code
    url = f"https://calendarific.com/api/v2/holidays?api_key={CALENDARIFIC_API_KEY}&country={country_code}&year={start_date.year}"
    if state:
        url += f"&location={state}"
    
    print(f"Calling Calendarific API with URL: {url}")
    resp = requests.get(url)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"API returned {len(data.get('response', {}).get('holidays', []))} total holidays")
        
        for hol in data.get("response", {}).get("holidays", []):
            date_str = hol["date"]["iso"][:10]
            date_obj = str_to_date(date_str)
            
            # Include all holidays in the date range, not just national holidays
            if start_date <= date_obj <= end_date:
                holidays.append({"date": date_str, "name": hol["name"]})
    else:
        print(f"API error: {resp.status_code} - {resp.text}")
        
    print(f"Returning {len(holidays)} holidays in the date range")
    return holidays


def find_vacation_breaks(start_date, end_date, weekends, holidays):
    # Build calendar from start_date to end_date
    breaks = []
    all_days = []
    day = start_date
    holiday_dates = {str_to_date(h["date"]): h["name"] for h in holidays}
    weekend_idxs = [WEEKDAYS.index(w) for w in weekends]
    while day <= end_date:
        info = {
            "date": day,
            "is_weekend": day.weekday() in weekend_idxs,
            "is_holiday": day in holiday_dates,
            "holiday_name": holiday_dates.get(day, None)
        }
        all_days.append(info)
        day += timedelta(days=1)

    # Find breaks with specific criteria:
    # - At least 5 days total
    # - At most 1 optional leave
    # - At most 2 weekend days
    # - Rest must be genuine holidays
    n = len(all_days)
    for i in range(n):
        for window in range(5, min(15, n-i+1)):  # check windows of length 5 to 14 days
            if i+window > n:
                continue
            chunk = all_days[i:i+window]
            num_holidays = sum(1 for d in chunk if d["is_holiday"])
            num_weekends = sum(1 for d in chunk if d["is_weekend"] and not d["is_holiday"])
            leave_needed = window - (num_holidays + num_weekends)
            
            # Debug print
            print(f"Window: {[date_to_str(d['date']) for d in chunk]}, Holidays: {num_holidays}, Weekends: {num_weekends}, Leave Needed: {leave_needed}")
            
            # Apply our criteria:
            # - Total days must be at least 5
            # - No more than 1 optional leave day
            # - No more than 2 weekend days
            # - At least 3 genuine holidays
            if leave_needed <= 1 and num_weekends <= 2 and num_holidays >= 3 and (window >= 5):
                # Calculate days by type for the description
                holiday_days = [d for d in chunk if d["is_holiday"]]
                weekend_days = [d for d in chunk if d["is_weekend"] and not d["is_holiday"]]
                leave_days = [d for d in chunk if not d["is_holiday"] and not d["is_weekend"]]
                
                # Create description with days categorized
                description = {}
                for d in chunk:
                    date_str = date_to_str(d["date"])
                    if d["is_holiday"]:
                        description[date_str] = d["holiday_name"]
                    elif d["is_weekend"]:
                        description[date_str] = "Weekend"
                    else:
                        description[date_str] = "Optional Leave"
                
                break_info = {
                    "start": date_to_str(chunk[0]["date"]),
                    "end": date_to_str(chunk[-1]["date"]),
                    "total_days": window,
                    "holiday_days": num_holidays,
                    "weekend_days": num_weekends,
                    "leave_days_needed": leave_needed,
                    "description": description
                }
                # Avoid duplicates (overlapping windows)
                if not breaks or breaks[-1]["end"] != break_info["end"]:
                    breaks.append(break_info)
    return breaks

@app.route('/api/vacations', methods=['POST'])
def get_vacations():
    data = request.json
    location = data.get("location", {"country": "India", "state": "Maharashtra"})
    weekends = data.get("weekend_days", ["Saturday", "Sunday"])
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    if not start_date or not end_date:
        today = datetime.now().date()
        start_date = today
        end_date = datetime(today.year, 12, 31).date()
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    holidays = get_holidays(start_date, end_date, location)
    breaks = find_vacation_breaks(start_date, end_date, weekends, holidays)
    return jsonify({"breaks": breaks})

@app.route('/api/holidays', methods=['POST'])
def get_all_holidays():
    data = request.json
    location = data.get("location", {"country": "India", "state": "Maharashtra"})
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    if not start_date or not end_date:
        today = datetime.now().date()
        start_date = today
        end_date = datetime(today.year, 12, 31).date()
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    holidays = get_holidays(start_date, end_date, location)
    return jsonify({"holidays": holidays})

if __name__ == '__main__':
    app.run(debug=True, port=5050)
