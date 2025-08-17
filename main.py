from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import asyncio
import dotenv
import requests
import pprint
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image
import io

dotenv.load_dotenv()

# Regular expression pattern for dd/mm/yyyy or dd/mm/yy with optional time (HH:MM)
DATE_PATTERN = re.compile(
    r'\b\d{1,2}/\d{1,2}(?:/(?:\d{2}|\d{4}))?(?:\s+\d{2}:\d{2})?\b'
)

# Telegram 
BOT_TOKEN: str | None = os.getenv("BOT_TOKEN") or ''
DAVID_CHAT_ID: str = os.getenv("DAVID_ID") or ''
SHIR_CHAT_ID: str = os.getenv("SHIR_ID") or ''
ELAD_CHAT_ID: str = os.getenv("ELAD_ID") or ''
CHAT_ID: list[str] =  [ DAVID_CHAT_ID],# SHIR_CHAT_ID, ELAD_CHAT_ID ]
SELENIUM_URL: str = os.getenv("SELENIUM_URL") or 'http://localhost:4444/wd/hub'
GAMES: dict = {}

def get_paragraphs_with_dates(url) -> None:
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=500,1080")

    # Connect to Selenium Grid (update the URL to your grid hub)
    driver = webdriver.Remote(
        command_executor=SELENIUM_URL,  # Change to your grid address
        options=chrome_options
    )

    try:
        driver.get(url)

        # Take full screenshot
        png = driver.get_screenshot_as_png()
        image = Image.open(io.BytesIO(png))
        # Crop to match Playwright's clip
        cropped = image.crop((50, 460, 450, 750))  # (left, upper, right, lower)
        cropped.save("latestGame.png")

        # Hebrew day names for matching
        HEBREW_DAYS = [
            "יום ראשון", "יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "יום שבת",
            "ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"
        ]

        # Get all paragraph elements
        paragraphs = [p.text for p in driver.find_elements(By.TAG_NAME, "p")]
        num = 0
        for i, paragraph in enumerate(paragraphs):
            if DATE_PATTERN.search(paragraph):
                # Extract day (first match from HEBREW_DAYS)
                game_day = next((d for d in HEBREW_DAYS if d in paragraph), "")

                # Extract date (first match of DATE_PATTERN)
                date_match = DATE_PATTERN.search(paragraph)
                game_date = date_match.group(0) if date_match else ""

                # Extract time (last match of HH:MM)
                time_match = re.findall(r'\d{1,2}:\d{2}', paragraph)
                game_time = time_match[-1] if time_match else ""

                # Remove game_time from game_date if present
                if game_time and game_time in game_date:
                    game_date = game_date.replace(game_time, "").strip()

                # print(f"When: {game_day} - {game_date} - {game_time}")

                try:
                    # Try parsing with short year
                    GAMES[num] =  {
                        "who": f"{paragraphs[i-1]} נגד {paragraphs[i+1]}",
                        "when": datetime.strptime(f"{game_date} {game_time}", '%d/%m/%y %H:%M'),
                        "day": game_day
                    }
                except ValueError:
                    try:
                        # Try parsing with long year
                        GAMES[num] =  {
                            "who": f"{paragraphs[i-1]} נגד {paragraphs[i+1]}",
                            "when": datetime.strptime(f"{game_date} {game_time}", '%d/%m/%Y %H:%M'),
                            "day": game_day
                        }
                    except ValueError:
                        # Try parsing without year (assume current year)
                        try:
                            this_year = datetime.now().year
                            GAMES[num] =  {
                                "who": f"{paragraphs[i-1]} נגד {paragraphs[i+1]}",
                                "when": datetime.strptime(f"{game_date}/{this_year} {game_time}", '%d/%m/%Y %H:%M'),
                                "day": game_day
                            }
                        except Exception as e:
                            print(f"Failed to parse date/time for paragraph: {paragraph} ({e})")
                num += 1
    finally:
        driver.quit()

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
    """
    Checks the scheduled games and sends notifications if there are games today after 12 PM or tomorrow after 12 PM.

    Args:
        is_debug (bool): If True, uses a fixed datetime for testing purposes. Defaults to False.
    """
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    if is_debug:
        pprint.pprint(GAMES, indent=4)
        now = now.replace(year=2025, month=7, day=18, hour=20)  
        
    for event in GAMES.values():
        event_time = event['when']
        event_teams = event['who']
        event_day = event['day']

        current_time = now
        
        is_event_after_noon = event_time.hour >= 12
        is_today_after_noon = event_time.date() == current_time.date() and is_event_after_noon  # Check if the event is today after 12 PM
        is_tomorrow = event_time.date() == (current_time + timedelta(days=1)).date()
        
        # Check if current time is 12 PM
        if current_time.hour == 12:
            if is_today_after_noon: # Check if the event is today after 12 PM
                send_event_reminder(event_teams, event_day, event_time, "היום")
                return
    
        # Check if current time is 8 PM
        elif current_time.hour == 20:
            if is_tomorrow and is_event_after_noon:
                send_event_reminder(event_teams, event_day, event_time, "מחר")
                return
    
    print("No Games in the next 24 hours. no message was sent.")


if __name__ == "__main__":
    try:
        url: str = r"https://www.haifa-stadium.co.il/%d7%9c%d7%95%d7%97_%d7%94%d7%9e%d7%a9%d7%97%d7%a7%d7%99%d7%9d_%d7%91%d7%90%d7%a6%d7%98%d7%93%d7%99%d7%95%d7%9f/"
        get_paragraphs_with_dates(url)
        check_and_notify(is_debug=False)
    except Exception as e:
        print(f"Exception: {e}")



