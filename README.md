# Purpose
Small telegram bot that webscarpes the University Hamburg Cafeteria website and can then 
tell you what's on the menu.

# How to use
1. Write @botfather on telegram and create a bot
2. Set the given bot token in the environment where the bot is running (MENSABOT_TOKEN). The bot 
script should run 24/7 or whichever availabiliy timing you want. 
3. Start the bot by running the script `./start_bot_background.sh`. This will use `tmux` or `nohup` if `tmux` isn't available.
Alternatively use the given `docker-compose.yaml`.

# Handling updates of the bot (migrating)
In case you want to use the bot after some update, I'd recommend running migrate.py to ensure
your db file fits the new bot code.
In the dockerized setting, change the CMD to run the migration script, start the docker container
with the old .db file mounted, then stop the container after migration is done and change the CMD back.
