#!/bin/bash

cd /home/vncuser/discord-ai-self

while true; do
    echo "Starting Discord AI Selfbot at $(date)"
    python3 main.py
    echo "Bot crashed at $(date), restarting in 5 seconds..."
    sleep 5
done
