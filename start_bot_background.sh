#!/bin/sh

# check if tmux is installed
if ! command -v tmux &> /dev/null
then
    echo "tmux could not be found, using nohup instead"
    echo "The output will be saved in mensabotout.txt"
    nohup python3 -u mensabot.py > mensabotout.txt 2>&1 &
    exit 0
fi

# run with tmux
tmux new -d -s mensabot_session 'python3 -u mensabot.py > mensabotout.txt'
