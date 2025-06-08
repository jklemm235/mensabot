# Purpose
Small telegram bot that webscarpes the University Hamburg Cafeteria website and can then 
tell you what's on the menu.

# How to use
1. Write @botfather on telegram and create a bot
2. Set the given bot token in the environment where the bot is running (MENSABOT_TOKEN). The bot 
script should run 24/7 or whichever availabiliy timing you want. 
3. Start the bot by running the script `./start_bot_background.sh`. This will use `tmux` or `nohup` if `tmux` isn't available.
4. Register the commands of the bot by writing `\setcommands` to @botfather. 
To see the commands, write the bot a /help message or check the `help_message` function in 
`mensabot.py`. Please note that botfather ecpects the commands as `command - desc`, so remove the slashes, e.g. change `/help - Give help message` to `help - Give help message`

# Handling updates of the bot (migrating)
In case you want to use the bot after some update, I'd recommend running migrate.py to ensure
your db file fits the new bot code
