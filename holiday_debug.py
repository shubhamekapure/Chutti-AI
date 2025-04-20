import requests
from datetime import datetime, timedelta

CALENDARIFIC_API_KEY = 'w84rTTpYA4rXrRZdYqhQzOI8V8ndxmG8'
country = 'IN'
start_date = datetime(2025,4,20)
end_date = datetime(2025,12,31)
url = f'https://calendarific.com/api/v2/holidays?api_key={CALENDARIFIC_API_KEY}&country={country}&year=2025'
data = requests.get(url).json()
holidays = []
for hol in data['response']['holidays']:
    date_str = hol['date']['iso'][:10]
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    if start_date <= date_obj <= end_date and hol.get('type') and 'National holiday' in hol['type']:
        holidays.append({'date': date_str, 'name': hol['name']})
print('Total holidays:', len(holidays))
print('Holiday dates:', [h['date'] for h in holidays])
