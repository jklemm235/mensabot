# pyright: reportGeneralTypeIssues=false
# pylint: disable=broad-except
import os
import time
import random

import mensascraping as scraper
from scheduler import Scheduler
from telegram_bot_admin import TelegramBotAdmin

RANDOM_MESSAGE_TO_ADD = [
    "Seagulls can drink saltwater as they have special salt glands, allowing them to cry out salty tears, saltier than the ocean itself!",
    "Honey never spoils (if stored correctly)",
    "Octopuses have three hearts and blue blood. Two hearts pump blood to the gills, while the third pumps it to the rest of the body!",
    "Octopuses have small brains in each of their eight arms, allowing them to taste and touch with their limbs independently! They truely life the federated lifestyle.",
    "Wombat poop is cube-shaped! This unique shape helps prevent the poop from rolling away, marking their territory effectively.",
    "A group of flamingos is called a 'flamboyance'.",
    "Sharks have been around longer than trees! They have existed for over 400 million years, while the first trees appeared around 350 million years ago.",
    "Sharks have survived all five major mass extinction events in Earth's history. This is because they are so god damn smooth",
    "The biggest organism on Earth is a fungus! It covers an area of nearly 10 square kilometers and is called humongous fungus.",
    "Philturm is vastly superior to Blattwerk in every way imaginable. It's a true fact.",
]

# --- Handler locations message ---
def locations_message() -> str:
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
        location_name = list(closest_locations.keys())[0]  # Use the match
        location_id = closest_locations[location_name]

    try:
        food_items = scraper.scrape_food_by_location(html.text, location_id)
    except Exception as e:
        return f"Error extracting food items for location ID {location_id}: {e}"

    if not food_items:
        return f"No food items found for {location_name} ({location_id}){extra_location_string} on {timepoint_str}."

    # Format the food items into a message
    food_msg = f"Food items for {location_name} ({location_id}){extra_location_string}:\n"
    for item in food_items:
        food_msg += f"- {item['name']} ({item['category']}): {item['prices']} on {item['date']}\n\n"
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
            food_msg += "\nP.S. Help, I couldn't find the Philturm location ID! "
            return food_msg

        food_msg += "\nP.S. Philturm:"
        try:
            philturm_food_items = scraper.scrape_food_by_location(html.text, philturm_location_id)
            food_msg += f"\nFood items for {philturm_location_name} ({philturm_location_id}):\n"
            for item in philturm_food_items:
                food_msg += f"- {item['name']} ({item['category']}): {item['prices']} on {item['date']}\n\n"
        except Exception as e:
            food_msg += f"Error extracting Philturm food items: {e}"

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
            food_msg += "\nP.S. Help, I couldn't find the Blattwerk location ID! "
            return food_msg

        food_msg += "\nP.S. Blattwerk:"
        try:
            blattwerk_food_items = scraper.scrape_food_by_location(html.text, blattwerk_location_id)
            food_msg += f"\nFood items for {blattwerk_location_name} ({blattwerk_location_id}):\n"
            for item in blattwerk_food_items:
                food_msg += f"- {item['name']} ({item['category']}): {item['prices']} on {item['date']}\n\n"
        except Exception as e:
            food_msg += f"Error extracting Blattwerk food items: {e}"

    # with 10% probability, add a random message
    if random.random() <= 0.1:
        food_msg += "\n\n" + random.choice(RANDOM_MESSAGE_TO_ADD)

    return food_msg

# --- Helper function for scheduled messages ---
def send_food_message(chat_id: int, location_id: str, bot_admin: TelegramBotAdmin, day_to_report: str = 'today'):
    """Sends a food message to the specified chat. Used by the scheduler."""
    try:
        food_msg = food_message(f"/food {location_id} {day_to_report}")
        bot_admin.send_message(chat_id, food_msg)
    except Exception as e:
        print(f"Error sending scheduled food message to chat {chat_id}: {e}")

# --- subscribe message ---
def handle_subscribe_message(message, scheduler_instance: Scheduler, chat_id, user_id, bot_admin: TelegramBotAdmin) -> None:
    """
    Receives /subscribe <location-id> <cron-days-of-week> <hh:mm> <day_to_report>
    and schedules cron-days-of-week times messages at hh:mm.
    cron-days-of-week is a string of the form "mon-fri" or "mon,tue,wed,thu,fri"...
    """
    split_message = message.split()
    if not(len(split_message) == 4 or len(split_message) == 5) or split_message[0] != "/subscribe":
        bot_admin.send_message(chat_id=chat_id,
                               text="Usage: /subscribe <location-id> <cron-days-of-week> <hh:mm> <day_to_report>" +\
               "E.g. /subscribe 176 mon-fri 10:00 today " +\
                "or /subscribe 176 mon,tue,wed,fri 10:00 tomorrow")
        return

    location_id = split_message[1]
    day_to_report = "today"  # Default value
    if len(split_message) > 4 and split_message[4].lower() in ["today", "tomorrow"]:
        day_to_report = split_message[4].lower()
    else:
        if len(split_message) == 5:
            bot_admin.send_message(chat_id=chat_id,
                                   text="Invalid day_to_report. Please use 'today' or 'tomorrow'.")
            return

    # Parse time
    time_str = split_message[3]
    try:
        time_parts = time_str.split(':')
        if len(time_parts) != 2:
            raise ValueError("Invalid time format")
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        if not (0 <= hour < 24) or not (0 <= minute < 60):
            raise ValueError("Invalid time values")
    except ValueError as e:
        bot_admin.send_message(chat_id, f"Invalid time format. Please use HH:MM (e.g., 10:00): {e}")
        return

    days_of_week = split_message[2]

    # Add schedule using the new Scheduler class
    try:
        schedule_id = scheduler_instance.add_schedule(
            function_name='send_food_message',
            chat_id=chat_id,
            user_id=user_id,
            args=(chat_id, location_id),
            kwargs={'bot_admin': bot_admin, 'day_to_report': day_to_report},
            day_of_week=days_of_week,
            hour=hour,
            minute=minute
        )
        bot_admin.send_message(chat_id=chat_id,
                               text=f"Subscribed to location {location_id} on {days_of_week} at {time_str}. " +\
                                   f"You will receive food updates at that time for the {'same' if day_to_report == 'today' else 'next'} day. " +
                                   f"Schedule ID: {schedule_id}")
    except Exception as e:
        bot_admin.send_message(chat_id, f"Error setting up subscription: {e}")
        return

def handle_unsubscribe_message(message, scheduler_instance: Scheduler, chat_id, user_id, chat_type, bot_admin: TelegramBotAdmin) -> None:
    """
    Receives /unsubscribe <schedule_id>
    and removes the subscription for that location.
    """
    split_message = message.split()
    if len(split_message) < 2:
        bot_admin.send_message(chat_id=chat_id,
                               text="Usage: /unsubscribe <schedule_ids>. You can find your schedule_id by using /listsubs.")
        return

    # Remove the job(s) from the database and scheduler
    removed_ids = []
    failed_ids = []
    for schedule_id_str in split_message[1:]:
        try:
            schedule_id = int(schedule_id_str)
            # Verify this schedule belongs to this user/chat before removing
            # For private chats: check user_id
            # For group chats: check chat_id
            schedules = scheduler_instance.get_schedules()
            found = False
            for sched_id, _, _args, _, _, sched_chat_id, sched_user_id in schedules:
                if sched_id == schedule_id:
                    # For private chats, verify user owns the schedule
                    # For group/supergroup chats, verify it's from this chat
                    if chat_type == 'private':
                        if sched_user_id == user_id:
                            found = True
                            break
                    else:  # group or supergroup
                        if sched_chat_id == chat_id:
                            found = True
                            break

            if not found:
                failed_ids.append(schedule_id_str)
                continue

            if scheduler_instance.remove_schedule(schedule_id):
                removed_ids.append(schedule_id_str)
            else:
                failed_ids.append(schedule_id_str)
        except ValueError:
            failed_ids.append(schedule_id_str)
            continue
        except Exception as e:
            print(f"Error removing schedule {schedule_id_str}: {e}")
            failed_ids.append(schedule_id_str)
            continue

    if removed_ids:
        bot_admin.send_message(chat_id=chat_id,
                               text=f"Unsubscribed from schedule IDs: {', '.join(removed_ids)}. " +\
                                    "You will no longer receive food updates for these subscriptions.")
    if failed_ids:
        bot_admin.send_message(chat_id=chat_id,
                               text=f"Could not remove schedule IDs: {', '.join(failed_ids)}. " +\
                                    "They may not exist or don't belong to you.")
    if not removed_ids and not failed_ids:
        bot_admin.send_message(chat_id=chat_id,
                               text="No valid schedule IDs provided. Please use /listsubs to see your subscriptions.")

def handle_list_subscriptions_message(scheduler_instance: Scheduler, bot_admin: TelegramBotAdmin, chat_id, user_id, chat_type) -> None:
    """
    Receives /listsubs and lists all subscriptions for the user.
    For private chats: shows schedules created by this user
    For group chats: shows schedules created in this chat
    """
    try:
        # Filter schedules based on chat type
        if chat_type == 'private':
            # In private chats, show all schedules created by this user
            schedules = scheduler_instance.get_schedules(user_id=user_id)
        else:  # group or supergroup
            # In group chats, show all schedules created in this chat
            schedules = scheduler_instance.get_schedules(chat_id=chat_id)
    except Exception as e:
        bot_admin.send_message(chat_id, f"Error retrieving subscriptions: {e}")
        return

    if not schedules:
        bot_admin.send_message(chat_id, "You have no active subscriptions.")
        return

    response = "Your active subscriptions:\n"
    for schedule_id, _function_name, args, kwargs, cron_config, _sched_chat_id, _sched_user_id in schedules:
        location_id = args[1] if len(args) > 1 else "Unknown"
        day_to_report = kwargs.get('day_to_report', 'today')
        day_of_week = cron_config['day_of_week']
        hour = cron_config['hour']
        minute = cron_config['minute']
        response += f"Schedule ID: {schedule_id}, Location: {location_id}, Days: {day_of_week}, " \
                   f"Time: {hour:02d}:{minute:02d}, Day To Report: {day_to_report}\n"

    bot_admin.send_message(chat_id, response)

# --- Main function to set up and run the bot ---
def main() -> None:
    """Starts the bot."""
    BOT_TOKEN = os.getenv("MENSABOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("Please set your bot token in the MENSABOT_TOKEN environment variable.")

    # Initialize TelegramBotAdmin
    bot_admin = TelegramBotAdmin(BOT_TOKEN)

    # Register commands
    bot_admin.register_command("locations", "Get a list of Mensa locations and their ids", None)
    bot_admin.register_command("food",
                               "<location-id/name> [today|tomorrow]: Get the food menu for a given location. " +
                               "If a name is provided, it will try to match the name to a location. " +
                               "Timepoint defaults to 'today' if not specified.", None)
    bot_admin.register_command("subscribe",
                               "<location-id> <cron-days> <hh:mm> <day_to_report: today/tomorrow> - " +
                               "Subscribe to receive food updates for a specific location at specific day(s) for either the same day or the next day. " +
                               "<cron-days> is a string of the form 'mon-fri' or 'sun,tue'", None)
    bot_admin.register_command("unsubscribe",
                               "<schedule_ids> - Unsubscribe from the food updates for a specific location at a specific time.", None)
    bot_admin.register_command("listsubs", "List all your subscriptions.", None)

    # Set commands in Telegram API
    bot_admin.set_bot_commands()

    # Initialize the scheduler and load schedules from database
    scheduler_instance = Scheduler()
    scheduler_instance.register_function(send_food_message)
    # Pass bot_admin as runtime kwargs so it gets injected into all scheduled function calls
    scheduler_instance.load_schedules_from_db(runtime_kwargs={'bot_admin': bot_admin})
    # Start the scheduler after functions are registered and schedules loaded
    scheduler_instance.start()

    while True:
        time.sleep(1) # anyways longpolling in the poll method
        try:
            # Poll for one update at a time (auto-handles help command)
            processed = bot_admin.poll_updates()
        except Exception as e:
            print(f"Error: {e}. Retrying in 3 seconds...")
            continue

        # If None, no updates available
        if processed is None:
            continue

        # Extract the processed update information
        update_id = processed['update_id']
        chat_id = processed['chat_id']
        user_id = processed['user_id']
        chat_type = processed['chat_type']
        message_text = processed['message_text']

        # If it was auto-handled (e.g., help command), skip further processing
        if processed.get('handled', False):
            continue

        print(f"Handling update {update_id} for chat {chat_id}: {message_text}")
        try:
            if message_text.startswith("/locations"):
                response = locations_message()
                bot_admin.send_message(chat_id, response)
            elif message_text.startswith("/food"):
                response = food_message(message_text)
                bot_admin.send_message(chat_id, response)
            elif message_text.startswith("/subscribe"):
                handle_subscribe_message(message_text, scheduler_instance, chat_id, user_id, bot_admin)
            elif message_text.startswith("/unsubscribe"):
                handle_unsubscribe_message(message_text, scheduler_instance, chat_id, user_id, chat_type, bot_admin)
            elif message_text.startswith("/listsubs"):
                handle_list_subscriptions_message(scheduler_instance, bot_admin, chat_id, user_id, chat_type)
            else:
                response = "Unknown command. Please use /help to see available commands."
                bot_admin.send_message(chat_id, response)
        except Exception as e:
            print(f"Error handling update {update_id}: {e}")




if __name__ == "__main__":
    main()
