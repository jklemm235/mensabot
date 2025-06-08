#!/bin/sh
# install requirements
if [ ! -f requirements.txt ]; then
    echo "requirements.txt not found, please ensure you are in the correct directory."
    exit 1
fi
if ! command -v python3 &> /dev/null
then
    echo "python3 could not be found, please install Python3."
    exit 1
fi

python3 -m pip install -r requirements.txt

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
