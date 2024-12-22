from playwright.async_api import async_playwright
from datetime import datetime, time, timedelta
import asyncio
import dotenv
import requests
import pprint
import os
import re

dotenv.load_dotenv()

# Regular expression pattern for dd/mm/yyyy or dd/mm/yy with optional time (HH:MM)
date_pattern = re.compile(
    r'\b\d{2}/\d{2}/(\d{2}|\d{4})(?:\s+\d{2}:\d{2})?\b'
)
games = {}
url = r"https://www.haifa-stadium.co.il/%d7%9c%d7%95%d7%97_%d7%94%d7%9e%d7%a9%d7%97%d7%a7%d7%99%d7%9d_%d7%91%d7%90%d7%a6%d7%98%d7%93%d7%99%d7%95%d7%9f/"

# Telegram 
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID =  [os.getenv("DAVID_ID"),os.getenv("SHIR_ID")]

async def get_paragraphs_with_dates(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Get all paragraph elements
        paragraphs = await page.locator("p").all_text_contents()
        num = 0
        for i, paragraph in enumerate(paragraphs):
            if date_pattern.search(paragraph):
                game_date = paragraph.split(" ")[1].replace('\xa0', '')
                game_time = paragraph.split(" ")[2].replace('\xa0', '')
                # print(f"When: {game_date} - {game_time}")
                
                try:
                    games[num] =  {
                        "who": f"{paragraphs[i-1]} נגד {paragraphs[i+1]}",
                        "when": datetime.strptime(f"{game_date} {game_time}", '%d/%m/%y %H:%M')
                    }
                    # print(datetime.strptime(f"{game_date} {game_time}", '%d/%m/%y %H:%M'))
                except ValueError:
                    games[num] =  {
                        "who": f"{paragraphs[i-1]} נגד {paragraphs[i+1]}",
                        "when": datetime.strptime(f"{game_date} {game_time}", '%d/%m/%Y %H:%M')
                    }
                    # print(datetime.strptime(f"{game_date} {game_time}", '%d/%m/%Y %H:%M'))
                num += 1
        await browser.close()

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for id in chat_id:
        payload = {
            "chat_id": id,
            "text": message
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print(f"Failed to send message: {response.text}")

def check_and_notify():
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    # now = datetime(2024, 12, 26, 14, 1).replace(minute=0, second=0, microsecond=0) # for tests
    today = now.date()

    start_time_8_pm = now.replace(hour=20, minute=0, second=0, microsecond=0)
    end_time_8_pm = start_time_8_pm + timedelta(days=1, minutes=59)
    
    for event in games.values():
        event_time = event['when']
        event_teams = event['who']
        
        delta = event_time - now
        delta_minutes = delta.seconds / 60
        delta_hours = delta_minutes / 60
        
        # 24-hour check at 8 PM
        if (0 < delta.days < 2)  or  (delta.days < 1 and delta_hours >= 20):  # Enable entire 8 PM hour
            if start_time_8_pm <= event_time <= end_time_8_pm:
                message = f"⚽ תזכורת: \n⚽{event_teams} \n⚽ מחר ב - {event_time.strftime('%H:%M')}"
                send_telegram_message(BOT_TOKEN, CHAT_ID, message)
                return
        
        # 12 PM same day check
        elif delta.days == 0 and delta_hours >= 3:
            if event_time.date() == today and event_time.time() >= now.time():
                message = f"⚽ תזכורת: \n⚽ {event_teams} \n⚽ היום ב - {event_time.strftime('%H:%M')}"
                send_telegram_message(BOT_TOKEN, CHAT_ID, message)
                return
    
    print("No Games in the next 24 hours. no message was sent.")
    # print(f"GAMES: {games}")
            


try:
    asyncio.run(get_paragraphs_with_dates(url))
    check_and_notify()
except Exception as e:
    print(f"Exception: {e}")
# pprint.pprint(games)


