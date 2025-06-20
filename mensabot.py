import os
import time
from typing import Optional
import random

import requests
from apscheduler.schedulers.background import BackgroundScheduler

import mensascraping as scraper
import schedulerLogic as sched
import schedulerDB as schedDB

OLE_MESSAGES = [
    "How is Otel going Ole?",
    "Ole, are you still working on Otel?",
    "Ole, I hope you're not too busy with Otel to enjoy some Mensa food!",
    "Ole, remember to take breaks and enjoy some Mensa food while working on Otel!",
    "Sometimes I dream about Otel",
    "I think Ole might actually not be working on Otel :("
]

COMMANDS = {
    "help": "Show this help message",
    "locations": "Get a list of Mensa locations and their ids",
    "food": "<location-id/name> [today|tomorrow]: Get the food menu for a given location. " +
             "If a name is provided, it will try to match the name to a location. " +
             "Timepoint defaults to 'today' if not specified.",
    "subscribe": "<location-id> <cron-days> <hh:mm> <day_to_report: today/tomorrow> - " +
                  "Subscribe to receive food updates for a specific location at specific day(s) for either the same day or the next day. " +
                  "<cron-days> is a string of the form 'mon-fri' or 'sun,tue'",
    "unsubscribe": "<schedule_ids> - Unsubscribe from the food updates for a specific location at a specific time.",
    "listsubs": "List all your subscriptions."
}

# # --- Handler help message ---
def help_message(message) -> str:
    """Sends a message with information about the bot."""
    return "\n".join([f"/{cmd}: {desc}" for cmd, desc in COMMANDS.items()])

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
    Receives /food <location-id/name> [timepoint] and sends the menu.
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


    # get the location names from the html
    location_name = location_id
    try:
        all_locations = scraper.get_all_location_names_and_ids(html.text)
        found = False
        for key, value in all_locations.items():
            if value == location_id:
                location_name = key
                found = True
                break
    except Exception as e:
        return f"Error extracting location names: {e}"

    # If the location ID is not found, try to match it with a name
    extra_location_string = ""
    if not found:
        closest_locations, min_distance = scraper.get_closest_locations_by_pattern(location_id, all_locations)
        if len(closest_locations.keys()) == 0:
            return f"Location {location_name} not found. No similar locations found."
        if len(closest_locations.keys()) > 1:
            return f"Location {location_name} not found. Did you mean one of these?\n" + \
                    "\n".join([f"{name} ({id})" for name, id in closest_locations.items()])
        extra_location_string = f" (edit distance of {min_distance} to given pattern {location_name}) "
        location_name = list(closest_locations.keys())[0]  # Use the match
        location_id = closest_locations[location_name]

    try:
        food_items = scraper.scrape_food_by_location(html.text, location_id)
    except Exception as e:
        return f"Error extracting food items for location ID {location_id}: {e}"

    if not food_items:
        return f"No food items found for {location_name} ({location_id}){extra_location_string} on {timepoint_str}."

    # Format the food items into a message
    food_message = f"Food items for {location_name} ({location_id}){extra_location_string}:\n"
    for item in food_items:
        food_message += f"- {item['name']} ({item['category']}): {item['prices']} on {item['date']}\n\n"
    # Send the message with the food items

    # if the location name is Blattwerk, also report Philturm and leave a cheeky remark for Simon
    if "blattwerk" in location_name.lower():
        philturm_location_id = None
        philturm_location_name = None
        for location in all_locations:
            if "philturm" in location.lower():
                philturm_location_id = all_locations[location]
                philturm_location_name = location
                break
        if not philturm_location_id or not philturm_location_name:
            food_message += "\nP.S. Help, I couldn't find the Philturm location ID! "
            return food_message

        food_message += "\nP.S. Philturm:"
        try:
            philturm_food_items = scraper.scrape_food_by_location(html.text, philturm_location_id)
            food_message += f"\nFood items for {philturm_location_name} ({philturm_location_id}):\n"
            for item in philturm_food_items:
                food_message += f"- {item['name']} ({item['category']}): {item['prices']} on {item['date']}\n\n"
        except Exception as e:
            food_message += f"Error extracting Philturm food items: {e}"

    # If asking for philturm, also report Blattwerk
    if "philturm" in location_name.lower():
        blattwerk_location_id = None
        blattwerk_location_name = None
        for location in all_locations:
            if "blattwerk" in location.lower():
                blattwerk_location_id = all_locations[location]
                blattwerk_location_name = location
                break
        if not blattwerk_location_id or not blattwerk_location_name:
            food_message += "\nP.S. Help, I couldn't find the Blattwerk location ID! "
            return food_message

        food_message += "\nP.S. Blattwerk:"
        try:
            blattwerk_food_items = scraper.scrape_food_by_location(html.text, blattwerk_location_id)
            food_message += f"\nFood items for {blattwerk_location_name} ({blattwerk_location_id}):\n"
            for item in blattwerk_food_items:
                food_message += f"- {item['name']} ({item['category']}): {item['prices']} on {item['date']}\n\n"
        except Exception as e:
            food_message += f"Error extracting Blattwerk food items: {e}"

    # with 20% probability, add a random Ole message
    if random.random() <= 0.2:
        food_message += "\n\n" + random.choice(OLE_MESSAGES)

    return food_message

# --- subscribe message ---
def handle_subscribe_message(message, scheduler_instance, chat_id, token) -> None:
    """
    Receives /subscribe <location-id> <cron-days-of-week> <hh:mm> <day_to_report>
    and schedules cron-days-of-week times messages at hh:mm.
    cron-days-of-week is a string of the form "mon-fri" or "mon,tue,wed,thu,fri"...
    """
    split_message = message.split()
    if not(len(split_message) == 4 or len(split_message) == 5) or split_message[0] != "/subscribe":
        send_message(token=token,
                     chat_id=chat_id,
                     text="Usage: /subscribe <location-id> <cron-days-of-week> <hh:mm> <day_to_report>" +\
               "E.g. /subscribe 176 mon-fri 10:00 " +\
                "or /subscribe 176 mon,tue,wed,fri 10:00")
        return

    location_id = split_message[1]
    day_to_report = "today"  # Default value
    if len(split_message) > 4 and split_message[4].lower() in ["today", "tomorrow"]:
        day_to_report = split_message[4].lower()
    else:
        send_message(token=token,
                     chat_id=chat_id,
                     text="Invalid day_to_report. Please use 'today' or 'tomorrow'.")
        return
    try:
        sched.set_cron_like_job(scheduler_instance=scheduler_instance,
                               chat_id=chat_id,
                               location_id=location_id,
                               token=token,
                               time_str=split_message[3],
                               days_of_week=split_message[2],
                               day_to_report=day_to_report)
    except Exception as e:
        send_message(token, chat_id, f"Error setting up subscription: {e}")
        return
    # persist the schedule in the database
    try:
        schedDB.add_schedule_to_db(chat_id=str(chat_id),
                                   location_id=location_id,
                                   time_str=split_message[3],
                                   days_of_week=split_message[2])
    except Exception as e:
        send_message(token, chat_id, f"Error saving subscription to database: {e}")
        return
    send_message(token=token,
                    chat_id=chat_id,
                    text=f"Subscribed to location {location_id} on {split_message[2]} at {split_message[3]}. " +\
                        f"You will receive food updates at that time for the {'same' if day_to_report == 'today' else 'next'} day.")

def handle_unsubscribe_message(message, scheduler_instance, chat_id, token) -> BackgroundScheduler:
    """
    Receives /unsubscribe <schedule_id>
    and removes the subscription for that location.
    """
    split_message = message.split()
    if len(split_message) < 2:
        send_message(token=token,
                     chat_id=chat_id,
                     text="Usage: /unsubscribe <schedule_ids>. You can find your schedule_id by using /listsubs.")
        return scheduler_instance

    # remove the job(s) from the database
    removed_ids = []
    for schedule_id in split_message[1:]:
        try:
            schedDB.remove_schedule_from_db(chat_id=str(chat_id),
                                           row_id=int(schedule_id))
        except Exception as e:
            send_message(token, chat_id, f"Error removing job {schedule_id} from scheduler: {e}")
            continue

        removed_ids.append(schedule_id)

    if not removed_ids or len(removed_ids) == 0:
        send_message(token=token,
                     chat_id=chat_id,
                     text="No valid schedule IDs provided. Please use /listsubs to see your subscriptions.")
        return scheduler_instance

    # now we just restart the scheduler.  Not clean but works
    scheduler_instance.shutdown(wait=False)  # Stop the scheduler
    scheduler_instance = sched.startup_scheduler(token)  # Restart the scheduler
    send_message(token=token,
                 chat_id=chat_id,
                 text=f"Unsubscribed from schedule IDs: {', '.join(removed_ids)}. " +\
                      "You will no longer receive food updates for these subscriptions.")
    return scheduler_instance

def handle_list_subscriptions_message(message, token, chat_id) -> None:
    """
    Receives /listsubs and lists all subscriptions for the user.
    """
    try:
        schedules = schedDB.retrieve_schedules()
    except Exception as e:
        send_message(token, chat_id, f"Error retrieving subscriptions: {e}")
        return

    if not schedules:
        send_message(token, chat_id, "You have no active subscriptions.")
        return

    response = "Your active subscriptions:\n"
    for schedule in schedules:
        if schedule[0] == str(chat_id):  # Only show subscriptions for this user
            response += f"Location ID: {schedule[1]}, Days: {schedule[3]}, Time: {schedule[2]}, Day To Report: {schedule[4]} Schedule_id: {schedule[5]}\n"

    send_message(token, chat_id, response)

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

def report_commands(token: str) -> None:
    """Reports the available commands to the telegram API."""
    url = f"https://api.telegram.org/bot{token}/setMyCommands"
    payload = [{"command": cmd, "description": desc} for cmd, desc in COMMANDS.items()]
    for cmd, desc in COMMANDS.items():
        if len(desc) > 255:
            print(f"Warning: Description for command '{cmd}' is too long: {len(desc)} characters. Max is 255.")
            raise ValueError(f"Description for command '{cmd}' is too long: {len(desc)} characters. Max is 255.")
    response = requests.post(url, json={"commands": payload})
    if response.status_code != 200:
        raise Exception(f"Failed to set commands: {response.text}")
    print("Commands reported successfully to Telegram API.")
    print(response.text)

# --- Main function to set up and run the bot ---
def main() -> None:
    """Starts the bot."""
    BOT_TOKEN = os.getenv("MENSABOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("Please set your bot token in the MENSABOT_TOKEN environment variable.")
    last_handled_id = None

    report_commands(BOT_TOKEN)  # Report the available commands to the Telegram API
    scheduler_instance = sched.startup_scheduler(BOT_TOKEN)  # Start the scheduler
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
                elif message_text.startswith("/subscribe"):
                    handle_subscribe_message(message_text, scheduler_instance, chat_id, BOT_TOKEN)
                elif message_text.startswith("/unsubscribe"):
                    scheduler_instance = handle_unsubscribe_message(message_text, scheduler_instance, chat_id, BOT_TOKEN)
                elif message_text.startswith("/listsubs"):
                    handle_list_subscriptions_message(message_text, BOT_TOKEN, chat_id)
                else:
                    response = "Unknown command. Please use /help to see available commands."
                    send_message(BOT_TOKEN, chat_id, response)
            except Exception as e:
                print(f"Error handling update {update_id}: {e}")


        #{'ok': True, 'result': [{'update_id': 67470315, 'message': {'message_id': 2, 'from':
        # {'id': 832431586, 'is_bot': False, 'first_name': 'Jay', 'last_name': 'Kay',
        # 'username': 'JayKay12792', 'language_code': 'en'}, 'chat': {'id': 832431586, 'first_name': 'Jay',
        # 'last_name': 'Kay', 'username': 'JayKay12792', 'type': 'private'}, 'date': 1748799535, 'text': 'Test'}}]}




if __name__ == "__main__":
    main()
