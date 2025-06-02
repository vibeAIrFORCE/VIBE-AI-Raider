#!/usr/bin/env python3
# VIBE AI Raider Bot - Twitter API Integration
# Built with 💖 by VIBE AI - Where quirky meets powerful tech!

# Copyright (c) 2024 VIBE AI Corp.
# Website: www.vibe.airforce
# Telegram: t.me/VIBEaiRforce
# X: x.com/VIBEaiRforce
# Docs: github.com/vibeAIrFORCE/Docs

import re
import logging
import random
import tweepy
import time
from config import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    MOCK_MODE
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TwitterAPI:
    """Twitter API integration for raid bot"""
    
    def __init__(self):
        """Initialize Twitter API client"""
        self.api = None if MOCK_MODE else self._setup_api()
        self.mock_mode = MOCK_MODE
        self._mock_metrics_store = {}  # Store for mock metrics
        
        if self.mock_mode:
            logger.info("Running in MOCK MODE - Twitter API calls will be simulated")
    
    def _setup_api(self):
        """Set up and return Twitter API client"""
        try:
            auth = tweepy.OAuth1UserHandler(
                TWITTER_API_KEY,
                TWITTER_API_SECRET,
                TWITTER_ACCESS_TOKEN,
                TWITTER_ACCESS_SECRET
            )
            return tweepy.API(auth)
        except Exception as e:
            logger.error(f"Error setting up Twitter API: {e}")
            return None
    
    def extract_tweet_id(self, tweet_url):
        """Extract tweet ID from a Twitter URL"""
        # Twitter URL pattern
        pattern = r'twitter\.com\/\w+\/status\/(\d+)'
        match = re.search(pattern, tweet_url)
        if match:
            return match.group(1)
        
        # X.com URL pattern
        pattern = r'x\.com\/\w+\/status\/(\d+)'
        match = re.search(pattern, tweet_url)
        if match:
            return match.group(1)
            
        return None
    
    def get_tweet_metrics(self, tweet_id):
        """Get current metrics for a tweet"""
        if self.mock_mode:
            # Generate mock metrics for testing
            return self._get_mock_metrics(tweet_id)
            
        try:
            tweet = self.api.get_status(tweet_id)
            return {
                'likes': tweet.favorite_count,
                'retweets': tweet.retweet_count,
                # Comments count requires different API approach
                'comments': self._estimate_comment_count(tweet_id)
            }
        except Exception as e:
            logger.error(f"Error fetching tweet metrics: {e}")
            return {'likes': 0, 'retweets': 0, 'comments': 0}
    
    def _get_mock_metrics(self, tweet_id):
        """Generate mock metrics for testing without Twitter API"""
        # Initialize if this is the first call for this tweet
        if tweet_id not in self._mock_metrics_store:
            self._mock_metrics_store[tweet_id] = {
                'likes': random.randint(5, 15),
                'retweets': random.randint(2, 8),
                'comments': random.randint(1, 5),
                'last_update': time.time(),
                'update_count': 0
            }
            logger.info(f"Initialized mock metrics for tweet {tweet_id}: {self._mock_metrics_store[tweet_id]}")
            return {
                'likes': self._mock_metrics_store[tweet_id]['likes'],
                'retweets': self._mock_metrics_store[tweet_id]['retweets'],
                'comments': self._mock_metrics_store[tweet_id]['comments']
            }
        
        # Update metrics based on time elapsed since last update
        current_time = time.time()
        time_elapsed = current_time - self._mock_metrics_store[tweet_id]['last_update']
        update_count = self._mock_metrics_store[tweet_id]['update_count'] + 1
        
        # More frequent updates in the beginning, slower over time
        if update_count < 5:
            like_increase = random.randint(3, 7)
            rt_increase = random.randint(1, 3)
            comment_increase = random.randint(1, 2)
        elif update_count < 10:
            like_increase = random.randint(2, 5)
            rt_increase = random.randint(1, 2)
            comment_increase = random.randint(0, 1)
        else:
            like_increase = random.randint(1, 3)
            rt_increase = random.randint(0, 1)
            comment_increase = random.randint(0, 1)
        
        # Update the stored metrics
        self._mock_metrics_store[tweet_id]['likes'] += like_increase
        self._mock_metrics_store[tweet_id]['retweets'] += rt_increase
        self._mock_metrics_store[tweet_id]['comments'] += comment_increase
        self._mock_metrics_store[tweet_id]['last_update'] = current_time
        self._mock_metrics_store[tweet_id]['update_count'] = update_count
        
        # Log the updated metrics
        logger.info(f"Updated mock metrics for tweet {tweet_id}: {self._mock_metrics_store[tweet_id]}")
        
        # Return the current metrics
        return {
            'likes': self._mock_metrics_store[tweet_id]['likes'],
            'retweets': self._mock_metrics_store[tweet_id]['retweets'],
            'comments': self._mock_metrics_store[tweet_id]['comments']
        }
    
    def _estimate_comment_count(self, tweet_id):
        """Estimate comment count for a tweet"""
        try:
            # This is a simplified approach - in production you'd need
            # to implement a more sophisticated method using Twitter API v2
            # or by scraping the tweet page
            return 0  # Placeholder
        except Exception as e:
            logger.error(f"Error estimating comment count: {e}")
            return 0
    
    def is_valid_tweet(self, tweet_id):
        """Check if a tweet ID is valid and accessible"""
        # In mock mode, consider all tweet IDs valid immediately
        if self.mock_mode:
            logger.info(f"Mock mode: Considering tweet {tweet_id} valid without API check")
            return True
            
        # Only try API validation if not in mock mode
        try:
            self.api.get_status(tweet_id)
            return True
        except Exception as e:
            logger.error(f"Error validating tweet: {e}")
            return False
