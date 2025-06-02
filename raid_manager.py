#!/usr/bin/env python3
# VIBE AI Raider Bot - Raid Manager
# Built with 💖 by VIBE AI - Where quirky meets powerful tech!

# Copyright (c) 2024 VIBE AI Corp.
# Website: www.vibe.airforce
# Telegram: t.me/VIBEaiRforce
# X: x.com/VIBEaiRforce
# Docs: github.com/vibeAIrFORCE/Docs

import time
import logging
import threading
import requests
import json
from datetime import datetime, timedelta
from twitter_api import TwitterAPI
from config import BOT_NAME, DEFAULT_RAID_DURATION, STATUS_UPDATE_INTERVAL, TELEGRAM_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RaidManager:
    """Manages raid state and operations"""
    
    def __init__(self):
        """Initialize raid manager"""
        self.active_raids = {}  # Store active raids
        self.twitter_api = TwitterAPI()
        self.telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    
    def start_raid(self, application, chat_id, tweet_url, targets):
        """Start a new raid with the given parameters"""
        # Extract tweet ID
        tweet_id = self.twitter_api.extract_tweet_id(tweet_url)
        if not tweet_id:
            return False, "Invalid tweet URL. Please check and try again."
        
        # Validate tweet (this will automatically pass in mock mode)
        if not self.twitter_api.is_valid_tweet(tweet_id):
            return False, "Tweet not found or not accessible. Please check and try again."
        
        # Get initial metrics
        current_metrics = self.twitter_api.get_tweet_metrics(tweet_id)
        logger.info(f"Initial metrics for tweet {tweet_id}: {current_metrics}")
        
        # Create raid info
        raid_id = f"{chat_id}_{tweet_id}"
        end_time = datetime.now() + timedelta(minutes=DEFAULT_RAID_DURATION)
        
        raid_info = {
            'raid_id': raid_id,
            'tweet_id': tweet_id,
            'tweet_url': tweet_url,
            'targets': targets,
            'current_metrics': current_metrics,
            'start_time': datetime.now(),
            'end_time': end_time,
            'chat_id': chat_id,
            'status_message_id': None,
            'is_active': True,
            'update_count': 0  # Track number of updates
        }
        
        # Store raid info
        self.active_raids[raid_id] = raid_info
        
        # Start raid monitoring thread
        threading.Thread(
            target=self._monitor_raid,
            args=(raid_id,),
            daemon=True
        ).start()
        
        return True, raid_info
    
    def _send_telegram_message(self, chat_id, text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=None):
        """Send a message to Telegram using direct API call"""
        url = f"{self.telegram_api_url}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_web_page_preview
        }
        
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return response.json()['result']
            else:
                logger.error(f"Error sending message: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception sending message: {e}")
            return None
    
    def _edit_telegram_message(self, chat_id, message_id, text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=None):
        """Edit an existing message in Telegram using direct API call"""
        url = f"{self.telegram_api_url}/editMessageText"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_web_page_preview
        }
        
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return True
            else:
                # If message content hasn't changed, Telegram returns an error but it's not a real error
                if "message is not modified" in response.text:
                    return True
                logger.error(f"Error editing message: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception editing message: {e}")
            return False
    
    def _delete_telegram_message(self, chat_id, message_id):
        """Delete a message from Telegram using direct API call"""
        if not message_id:
            return False
            
        url = f"{self.telegram_api_url}/deleteMessage"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Error deleting message: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception deleting message: {e}")
            return False
    
    def _create_progress_bar(self, current, target, length=10):
        """Create a visual progress bar"""
        percentage = min(int((current / target) * 100), 100) if target > 0 else 0
        filled_length = int(length * current / target) if target > 0 else 0
        bar = '█' * filled_length + '░' * (length - filled_length)
        return f"{bar} {percentage}%"
    
    def _monitor_raid(self, raid_id):
        """Monitor raid progress and update status message"""
        raid_info = self.active_raids.get(raid_id)
        if not raid_info:
            logger.error(f"Raid {raid_id} not found in active raids")
            return
        
        logger.info(f"Starting raid monitoring for {raid_id}")
        logger.info(f"Targets: {raid_info['targets']}")
        
        # Create initial status message with buttons
        initial_message = self._send_telegram_message(
            chat_id=raid_info['chat_id'],
            text=self.format_raid_message(raid_info),
            reply_markup=self._create_raid_buttons(raid_id)
        )
        
        if initial_message:
            raid_info['status_message_id'] = initial_message['message_id']
            logger.info(f"Created initial status message for raid {raid_id}, message ID: {initial_message['message_id']}")
        else:
            logger.error(f"Failed to create initial status message for raid {raid_id}")
            return
        
        try:
            while raid_info['is_active']:
                # Check if raid should end due to time
                if datetime.now() >= raid_info['end_time']:
                    raid_info['is_active'] = False
                    logger.info(f"Raid {raid_id} ended due to time expiration")
                    
                    # Delete the old status message
                    if raid_info['status_message_id']:
                        self._delete_telegram_message(raid_info['chat_id'], raid_info['status_message_id'])
                    
                    # Send a new completion message
                    final_message = self._send_telegram_message(
                        chat_id=raid_info['chat_id'],
                        text=f"⏱ *{BOT_NAME} - RAID COMPLETED* - Time expired!\n\n" + 
                             self.format_raid_message(raid_info)
                    )
                    
                    # Remove from active raids
                    if raid_id in self.active_raids:
                        del self.active_raids[raid_id]
                    break
                
                # Update metrics
                raid_info['current_metrics'] = self.twitter_api.get_tweet_metrics(
                    raid_info['tweet_id']
                )
                
                # Log current metrics for debugging
                logger.info(f"Current metrics for raid {raid_id}: {raid_info['current_metrics']}")
                
                # Check if targets are met
                targets = raid_info['targets']
                current = raid_info['current_metrics']
                
                # Log comparison for debugging
                logger.info(f"Comparing - Likes: {current['likes']}/{targets['likes']}, " +
                           f"Retweets: {current['retweets']}/{targets['retweets']}, " +
                           f"Comments: {current['comments']}/{targets['comments']}")
                
                if (current['likes'] >= targets['likes'] and
                    current['retweets'] >= targets['retweets'] and
                    current['comments'] >= targets['comments']):
                    
                    raid_info['is_active'] = False
                    logger.info(f"Raid {raid_id} completed successfully - all targets met")
                    
                    # Delete the old status message
                    if raid_info['status_message_id']:
                        self._delete_telegram_message(raid_info['chat_id'], raid_info['status_message_id'])
                    
                    # Send a new success message
                    success_message = self._send_telegram_message(
                        chat_id=raid_info['chat_id'],
                        text=f"🎉 *{BOT_NAME} - RAID SUCCESSFUL* - All targets met!\n\n" + 
                             self.format_raid_message(raid_info)
                    )
                    
                    # Remove from active raids
                    if raid_id in self.active_raids:
                        del self.active_raids[raid_id]
                    break
                
                # Increment update count
                raid_info['update_count'] += 1
                
                # Every update, delete the old message and send a new one to make it appear as the newest message
                if raid_info['status_message_id']:
                    # Delete the old status message
                    self._delete_telegram_message(raid_info['chat_id'], raid_info['status_message_id'])
                
                # Send a new status message
                new_message = self._send_telegram_message(
                    chat_id=raid_info['chat_id'],
                    text=self.format_raid_message(raid_info),
                    reply_markup=self._create_raid_buttons(raid_id)
                )
                
                if new_message:
                    raid_info['status_message_id'] = new_message['message_id']
                    logger.info(f"Created new status message for raid {raid_id}, message ID: {new_message['message_id']}")
                else:
                    logger.error(f"Failed to create new status message for raid {raid_id}")
                
                # Wait for update interval before next update
                time.sleep(STATUS_UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"Error in raid monitoring: {e}")
            # Ensure raid is removed from active raids on error
            if raid_id in self.active_raids:
                del self.active_raids[raid_id]
    
    def _create_raid_buttons(self, raid_id):
        """Create inline keyboard buttons for raid actions"""
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '🔄 Refresh', 'callback_data': f'refresh_{raid_id}'},
                    {'text': '🛑 Cancel Raid', 'callback_data': f'cancel_{raid_id}'}
                ],
                [
                    {'text': '🔗 Open Tweet', 'url': self.active_raids[raid_id]['tweet_url']}
                ]
            ]
        }
        return keyboard
    
    def format_raid_message(self, raid_info):
        """Format raid status message with progress bars"""
        tweet_url = raid_info['tweet_url']
        end_time = raid_info['end_time']
        targets = raid_info['targets']
        current = raid_info['current_metrics']
        
        time_left = end_time - datetime.now()
        if time_left.total_seconds() <= 0:
            time_str = "0m 0s"
        else:
            minutes, seconds = divmod(time_left.seconds, 60)
            time_str = f"{minutes}m {seconds}s"
        
        # Calculate percentages safely
        like_pct = int((current['likes'] / targets['likes'] * 100) 
                      if targets['likes'] > 0 else 0)
        rt_pct = int((current['retweets'] / targets['retweets'] * 100) 
                    if targets['retweets'] > 0 else 0)
        comment_pct = int((current['comments'] / targets['comments'] * 100) 
                         if targets['comments'] > 0 else 0)
        
        # Create progress bars
        like_bar = self._create_progress_bar(current['likes'], targets['likes'])
        rt_bar = self._create_progress_bar(current['retweets'], targets['retweets'])
        comment_bar = self._create_progress_bar(current['comments'], targets['comments'])
        
        message = f"🚀 *{BOT_NAME} - RAID IN PROGRESS* 🚀\n\n"
        message += f"⏱ Time Remaining: {time_str}\n\n"
        message += "📊 *Progress*:\n"
        message += f"❤️ Likes: {current['likes']}/{targets['likes']}\n{like_bar}\n\n"
        message += f"🔄 Retweets: {current['retweets']}/{targets['retweets']}\n{rt_bar}\n\n"
        message += f"💬 Comments: {current['comments']}/{targets['comments']}\n{comment_bar}\n\n"
        message += "🏆 *Raid ends when all targets are met or time expires!*"
        
        return message
    
    def handle_callback_query(self, callback_query_id, callback_data, chat_id, user_id):
        """Handle callback queries from inline buttons"""
        logger.info(f"Handling callback query: {callback_data}")
        
        # Answer the callback query to stop the loading indicator
        self._answer_callback_query(callback_query_id)
        
        if callback_data.startswith('refresh_'):
            # Extract raid_id from callback data
            raid_id = callback_data[len('refresh_'):]
            
            # Check if raid exists
            if raid_id not in self.active_raids:
                return False, "Raid not found."
            
            # Update metrics immediately
            raid_info = self.active_raids[raid_id]
            raid_info['current_metrics'] = self.twitter_api.get_tweet_metrics(
                raid_info['tweet_id']
            )
            
            # Delete the old status message
            if raid_info['status_message_id']:
                self._delete_telegram_message(raid_info['chat_id'], raid_info['status_message_id'])
            
            # Send a new status message
            new_message = self._send_telegram_message(
                chat_id=raid_info['chat_id'],
                text=self.format_raid_message(raid_info),
                reply_markup=self._create_raid_buttons(raid_id)
            )
            
            if new_message:
                raid_info['status_message_id'] = new_message['message_id']
                logger.info(f"Created new status message for raid {raid_id}, message ID: {new_message['message_id']}")
                return True, "Raid status refreshed."
            else:
                logger.error(f"Failed to create new status message for raid {raid_id}")
                return False, "Failed to refresh raid status."
            
        elif callback_data.startswith('cancel_'):
            # Extract raid_id from callback data
            raid_id = callback_data[len('cancel_'):]
            
            # Cancel the raid
            if raid_id in self.active_raids:
                raid_info = self.active_raids[raid_id]
                
                # Delete the old status message
                if raid_info['status_message_id']:
                    self._delete_telegram_message(raid_info['chat_id'], raid_info['status_message_id'])
                
                # Send a cancellation message
                self._send_telegram_message(
                    chat_id=raid_info['chat_id'],
                    text=f"🛑 *{BOT_NAME} - RAID CANCELLED*\n\nThis raid has been cancelled by a user."
                )
                
                # Mark raid as inactive and remove from active raids
                raid_info['is_active'] = False
                del self.active_raids[raid_id]
                
                return True, "Raid cancelled successfully."
            else:
                return False, "Raid not found."
        
        return False, "Unknown callback query."
    
    def _answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        """Answer a callback query to stop the loading indicator"""
        url = f"{self.telegram_api_url}/answerCallbackQuery"
        payload = {
            'callback_query_id': callback_query_id
        }
        
        if text:
            payload['text'] = text
            payload['show_alert'] = show_alert
        
        try:
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return False
    
    def get_active_raids_count(self, chat_id=None):
        """Get count of active raids, optionally filtered by chat_id"""
        if chat_id:
            return sum(1 for raid in self.active_raids.values() 
                      if raid['chat_id'] == chat_id and raid['is_active'])
        return len(self.active_raids)
    
    def get_active_raids(self, chat_id=None):
        """Get list of active raids, optionally filtered by chat_id"""
        if chat_id:
            return [raid for raid in self.active_raids.values() 
                   if raid['chat_id'] == chat_id and raid['is_active']]
        return list(self.active_raids.values())
    
    def cancel_raid(self, chat_id, tweet_id=None):
        """Cancel a raid or all raids in a chat"""
        if tweet_id:
            # Cancel specific raid
            raid_id = f"{chat_id}_{tweet_id}"
            if raid_id in self.active_raids:
                # Delete the old status message
                if self.active_raids[raid_id]['status_message_id']:
                    self._delete_telegram_message(chat_id, self.active_raids[raid_id]['status_message_id'])
                
                # Send a cancellation message
                self._send_telegram_message(
                    chat_id=chat_id,
                    text=f"🛑 *{BOT_NAME} - RAID CANCELLED*\n\nThis raid has been cancelled by a user."
                )
                
                self.active_raids[raid_id]['is_active'] = False
                del self.active_raids[raid_id]
                return True, "Raid cancelled successfully."
            return False, "Raid not found."
        else:
            # Cancel all raids in chat
            cancelled = 0
            for raid_id in list(self.active_raids.keys()):
                if self.active_raids[raid_id]['chat_id'] == chat_id:
                    # Delete the old status message
                    if self.active_raids[raid_id]['status_message_id']:
                        self._delete_telegram_message(chat_id, self.active_raids[raid_id]['status_message_id'])
                    
                    # Send a cancellation message
                    self._send_telegram_message(
                        chat_id=chat_id,
                        text=f"🛑 *{BOT_NAME} - RAID CANCELLED*\n\nThis raid has been cancelled by a user."
                    )
                    
                    self.active_raids[raid_id]['is_active'] = False
                    del self.active_raids[raid_id]
                    cancelled += 1
            
            if cancelled > 0:
                return True, f"{cancelled} raid(s) cancelled successfully."
            return False, "No active raids found in this chat."