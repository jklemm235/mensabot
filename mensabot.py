import os
import time
from typing import Optional

import requests

import mensascraping as scraper

# # --- Handler help message ---
def help_message(message) -> str:
    """Sends a message with information about the bot."""
    help_text = \
        "Welcome to MensaBot! Here are the commands you can use:\n" +\
        "/help - Show this help message\n" +\
        "/locations - Get a list of Mensa locations and their ids\n" +\
        "/food <location-id> [today|tomorrow] - Get the food menu for a given location. " +\
        "Timepoint defaults to 'today' if not specified."
        # Add more commands as needed
    return help_text


# --- Handler locations message ---
def locations_message(message) -> str:
    """Sends a message with the list of Mensa locations."""
    try:
        html = scraper.get_html_by_day()
    except Exception as e:
         return f"Error fetching Mensa locations, could not receive the HTML: {e}"
    # Extract all Mensa locations and their IDs from the HTML
    try:
        locations = scraper.get_all_location_names_and_ids(html.text)
    except Exception as e:
        return f"Error extracting Mensa locations, could not extract the locations: {e}"

    if not locations:
        return "No Mensa locations found."


    location_text = "Available Mensa locations:\n"
    for location_name, location_id in locations.items():
        location_text += f"{location_name} (ID: {location_id})\n"

    return location_text

# --- Handler food message ---
def food_message(message) -> str:
    """
    Receives /food <location-id> [timepoint] and sends the menu.
    Timepoint defaults to 'today'.
    """
    split_message = message.split()
    if len(split_message) < 2 or len(split_message) > 3 or split_message[0] != "/food":
        return "Usage: /food <location-id> [today|tomorrow]. " +\
               "Timepoint defaults to 'today' if not specified."

    location_id = split_message[1]
    timepoint_str = "today" # Default value
    if len(split_message) > 2:
        # If a second argument is provided, use it as the timepoint
        timepoint_str = split_message[2].lower() # Convert to lowercase for easier comparison
        if timepoint_str not in ["today", "tomorrow"]:
            return "Invalid timepoint. Please use 'today' or 'tomorrow'."

    # --- Call your scraper function with location_id and target_date ---
    try:
        # Assuming get_food_menu_by_id and get_html_by_day exist in mensascraping
        html = scraper.get_html_by_day(t_query_param=timepoint_str)
    except Exception as e:
        return f"Error fetching the html: {e}"

    try:
        food_items = scraper.scrape_food_by_location(html.text, location_id)
    except Exception as e:
        return f"Error extracting food items for location ID {location_id}: {e}"

    if not food_items:
        return f"No food items found for location ID {location_id} on {timepoint_str}."

    # Format the food items into a message
    food_message = f"Food items for location ID {location_id} on {timepoint_str}:\n"
    for item in food_items:
        food_message += f"- {item['name']} ({item['category']}): {item['prices']} on {item['date']}\n\n"
    # Send the message with the food items
    return food_message

# telegram library sucks so we just call the API directly
def poll_updates(token: str, last_handled_id: Optional[int]) -> dict:
    """Polls updates from the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    response = requests.get(url, timeout=3600, params={"offset": last_handled_id+1} if last_handled_id is not None else {}) # long polling, but we still time out after 1 hour
    if response.status_code == 200:
        return response.json()
    return {}

def send_message(token: str, chat_id: int, text: str) -> None:
    """Sends a message to a Telegram chat."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    print(f"Sending message to chat {chat_id}: {text}")
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to send message: {response.text}")

# --- Main function to set up and run the bot ---
def main() -> None:
    """Starts the bot."""
    BOT_TOKEN = os.getenv("MENSABOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("Please set your bot token in the MENSABOT_TOKEN environment variable.")

    last_handled_id = None
    while True:
        time.sleep(10)
        try:
            # Poll for updates
            updates = poll_updates(BOT_TOKEN, last_handled_id)
        except Exception as e:
            print(f"Error: {e}. Retrying in 3 seconds...")
            continue

        # work with the updates
        if "result" not in updates:
            print("No updates found.")
            continue

        for update in updates['result']:
            update_id = update.get('update_id')
            last_handled_id = update_id
            try:
                chat_id = update['message']['chat']['id']
            except KeyError:
                print(f"Update {update_id} does not contain a message or chat ID. Skipping.")
                continue

            try:
                message_text = update['message']['text']
            except KeyError:
                print(f"Update {update_id} does not contain a text message. Skipping.")
                continue
            print(f"Handling update {update_id} for chat {chat_id}: {message_text}")
            try:
                if message_text.startswith("/help"):
                    response = help_message(message_text)
                    send_message(BOT_TOKEN, chat_id, response)
                elif message_text.startswith("/locations"):
                    response = locations_message(message_text)
                    send_message(BOT_TOKEN, chat_id, response)
                elif message_text.startswith("/food"):
                    response = food_message(message_text)
                    send_message(BOT_TOKEN, chat_id, response)
            except Exception as e:
                print(f"Error handling update {update_id}: {e}")


        #{'ok': True, 'result': [{'update_id': 67470315, 'message': {'message_id': 2, 'from':
        # {'id': 832431586, 'is_bot': False, 'first_name': 'Jay', 'last_name': 'Kay',
        # 'username': 'JayKay12792', 'language_code': 'en'}, 'chat': {'id': 832431586, 'first_name': 'Jay',
        # 'last_name': 'Kay', 'username': 'JayKay12792', 'type': 'private'}, 'date': 1748799535, 'text': 'Test'}}]}




if __name__ == "__main__":
    main()
