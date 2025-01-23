from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import asyncio
import dotenv
import requests
import pprint
import os
import re

dotenv.load_dotenv()

# Regular expression pattern for dd/mm/yyyy or dd/mm/yy with optional time (HH:MM)
DATE_PATTERN = re.compile(
    r'\b\d{2}/\d{2}/(\d{2}|\d{4})(?:\s+\d{2}:\d{2})?\b'
)

# Telegram 
BOT_TOKEN: str | None = os.getenv("BOT_TOKEN") or ''
DAVID_CHAT_ID: str = os.getenv("DAVID_ID") or ''
SHIR_CHAT_ID: str = os.getenv("SHIR_ID") or ''
ELAD_CHAT_ID: str = os.getenv("ELAD_ID") or ''
CHAT_ID: list[str] =  [ DAVID_CHAT_ID]#, SHIR_CHAT_ID, ELAD_CHAT_ID ]
GAMES: dict = {}

async def get_paragraphs_with_dates(url) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 500, "height": 1080})
        await page.goto(url)
        await page.screenshot(path="latestGame.png", clip={"x": 50, "y": 460, "width": 400, "height": 290})
        
        
        # Get all paragraph elements
        paragraphs = await page.locator("p").all_text_contents()
        num = 0
        for i, paragraph in enumerate(paragraphs):
            if DATE_PATTERN.search(paragraph):
                game_day = paragraph.split(" ")[0].replace('\xa0', '')
                game_date = paragraph.split(" ")[1].replace('\xa0', '')
                game_time = paragraph.split(" ")[2].replace('\xa0', '')
                # print(f"When: {game_date} - {game_time}")
                
                try:
                    GAMES[num] =  {
                        "who": f"{paragraphs[i-1]} נגד {paragraphs[i+1]}",
                        "when": datetime.strptime(f"{game_date} {game_time}", '%d/%m/%y %H:%M'), # 01/02/25 20:00
                        "day": game_day
                    }
                    # print(datetime.strptime(f"{game_date} {game_time}", '%d/%m/%y %H:%M'))
                except ValueError as e:
                    GAMES[num] =  {
                        "who": f"{paragraphs[i-1]} נגד {paragraphs[i+1]}",
                        "when": datetime.strptime(f"{game_date} {game_time}", '%d/%m/%Y %H:%M'), # 01/02/2025 20:00
                        "day": game_day
                    }
                    # print(datetime.strptime(f"{game_date} {game_time}", '%d/%m/%Y %H:%M'))
                num += 1
        await browser.close()

def send_telegram_message(bot_token: str, chat_id: list[str], message: str, parse_mode: str = 'HTML') -> None:
    url: str = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for id in chat_id:
        payload: dict = {
            "chat_id": id,
            "text": message,
            "parse_mode": parse_mode
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print(f"Failed to send message: {response.text}")
            
def send_telegram_photo(bot_token: str, chat_id: list[str], photo_path: str, caption: str = '', parse_mode: str = 'Markdown') -> None:
    url: str = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    for id in chat_id:
        with open(photo_path, 'rb') as photo:
            payload: dict = {
                "chat_id": id,
                "caption": caption,
                "parse_mode": parse_mode
            }
            files = {
                "photo": photo
            }
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print("Photo sent successfully!")
            else:
                print(f"Failed to send photo: {response.text}")

def send_event_reminder(event_teams, event_day, event_time, day_text) -> None:
    message = f"⚽ תזכורת: \n⚽ {event_teams} \n⚽ {day_text} ( {event_day} ) ב - {event_time.strftime('%H:%M')}"
    send_telegram_photo(BOT_TOKEN, CHAT_ID, "latestGame.png", caption=message, parse_mode='Markdown')

        
def check_and_notify(is_debug=False):
    if is_debug:
        pprint.pprint(GAMES, indent=4)
        now = datetime(2025, 2, 15, 12, 1).replace(minute=0, second=0, microsecond=0) 
    else:
        now = datetime.now().replace(minute=0, second=0, microsecond=0)   
        
    for event in GAMES.values():
        event_time = event['when']
        event_teams = event['who']
        event_day = event['day']

        current_time = now
        
        is_after_noon = event_time.hour >= 12
        is_today_after_noon = event_time.date() == current_time.date() and is_after_noon  # Check if the event is today after 12 PM
        is_tomorrow = event_time.date() == (current_time + timedelta(days=1)).date()
        
        # Check if current time is 12 PM
        if is_today_after_noon:
            if event_time.date() == current_time.date() and event_time.hour >= 12: # Check if the event is today after 12 PM
                send_event_reminder(event_teams, event_day, event_time, "היום")
                return
            
        # Check if current time is 8 PM
        elif current_time.hour == 20:
            if is_tomorrow and is_after_noon:
                send_event_reminder(event_teams, event_day, event_time, "מחר")
                return
    
    print("No Games in the next 24 hours. no message was sent.")


if __name__ == "__main__":
    try:
        url: str = r"https://www.haifa-stadium.co.il/%d7%9c%d7%95%d7%97_%d7%94%d7%9e%d7%a9%d7%97%d7%a7%d7%99%d7%9d_%d7%91%d7%90%d7%a6%d7%98%d7%93%d7%99%d7%95%d7%9f/"
        asyncio.run(get_paragraphs_with_dates(url))
        check_and_notify(is_debug=True)
    except Exception as e:
        print(f"Exception: {e}")



