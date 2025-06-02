#!/usr/bin/env python3
# VIBE AI Raider Bot - Configuration
# Built with 💖 by VIBE AI - Where quirky meets powerful tech!

# Copyright (c) 2024 VIBE AI Corp.
# Website: www.vibe.airforce
# Telegram: t.me/VIBEaiRforce
# X: x.com/VIBEaiRforce
# Docs: github.com/vibeAIrFORCE/Docs

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Information
BOT_NAME = "VIBE AI Raider"
BOT_VERSION = "1.0.0"

# Telegram Bot Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Twitter API Configuration
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')

# Raid Configuration
DEFAULT_RAID_DURATION = 30  # minutes
STATUS_UPDATE_INTERVAL = 20  # seconds

# Mock Mode (set to True if you don't have valid Twitter API credentials)
MOCK_MODE = True # Change to False when you have valid Twitter API credentials