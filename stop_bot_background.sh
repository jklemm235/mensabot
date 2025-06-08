#!/bin/sh

# check if tmux is installed
if ! command -v tmux &> /dev/null
then
    echo "tmux could not be found, asumin nohup was used instead"
    echo Please chose the processes to stop manually.
    ps aux | grep mensabot.py | grep -v grep
    exit 0
fi

# run with tmux
tmux kill-session -t mensabot_session
