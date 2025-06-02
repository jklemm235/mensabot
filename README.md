# Purpose
Small telegram bot that webscarpes the University Hamburg Cafeteria website and can then 
tell you what's on the menu.

# How to use
1. Write @botfather on telegram and create a bot
2. Set the given bot token in the environment where the bot is running (MENSABOT_TOKEN). The bot 
script should run 24/7 or whichever availabiliy timing you want. 
3. Start the bot by running the script, e.g. via `nohup python3 -u mensabot.py > out.txt 2>&1 &`
3. Register the commands of the bot by writing \setcommands to @botfather. 
To see the commands, write the bot a /help message or check the `help_message` function in 
`mensabot.py`
