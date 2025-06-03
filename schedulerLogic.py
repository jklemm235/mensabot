from apscheduler.schedulers.background import BackgroundScheduler

import schedulerDB as schedDB
import mensabot as bot

def send_food_message(chat_id: int, location_id: str, token: str):
    """Sends a food message to the specified chat."""
    try:
        food_message = bot.food_message(f"/food {location_id} today")
        bot.send_message(token, chat_id, food_message)
    except Exception as e:
        print(f"Error sending food message: {e}")

def set_cron_like_job(scheduler_instance: BackgroundScheduler, chat_id: str, location_id: str,
                      token: str, time_str: str = "10:00", days_of_week: str = 'mon-fri'):
    """Sets up a recurring 'cron-like' job."""
    # Set up daily messages from mo to fr at the specified time
    if not time_str:
        raise ValueError("Time string cannot be empty.")
    time_str_split = time_str.split(':')
    if len(time_str_split) != 2 or not all(part.isdigit() for part in time_str_split) or \
       not (0 <= int(time_str_split[0]) < 24) or not (0 <= int(time_str_split[1]) < 60) or \
       len(time_str_split[0]) != 2 or len(time_str_split[1]) != 2:
        raise ValueError("Time string must be in the format 'HH:MM' with valid hour and minute values.")

    scheduler_instance.add_job(send_food_message,
        'cron',
        day_of_week=days_of_week,
        hour=int(time_str.split(':')[0]),
        minute=int(time_str.split(':')[1]),
        args=[int(chat_id), location_id, token]
    )


def startup_scheduler(token: str):
    """
    Initializes the scheduler, reading from the database and setting the relevant jobs.
    Should be called at the start of the bot, not multiple times or we spam
    """
    scheduler = BackgroundScheduler()
    schedules = schedDB.retrieve_schedules()
    for schedule_item in schedules:
        chat_id = schedule_item[0]  # chat_id
        location_id = schedule_item[1]
        time_str = schedule_item[2]
        days_of_week = schedule_item[3]
        print(f"Setting up job for chat_id: {chat_id}, location_id: {location_id}, time: {time_str}, days: {days_of_week}")
        set_cron_like_job(scheduler_instance=scheduler,
                          chat_id=chat_id,
                          location_id=location_id,
                          token=token,
                          time_str=time_str,
                          days_of_week=days_of_week)

    # Start the scheduler process
    scheduler.start()
    return scheduler
