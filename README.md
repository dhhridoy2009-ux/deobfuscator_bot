# Deobfuscator Telegram Bot

## Files
- bot.py
- requirements.txt
- Dockerfile
- render.yaml
- README.md

## Render deployment
1. Upload all files to a GitHub repository.
2. Open Render and choose New -> Blueprint.
3. Select the GitHub repository.
4. Add the environment variable:
   BOT_TOKEN = your Telegram BotFather token
5. Deploy.

This bot uses polling and should run as a Background Worker.
