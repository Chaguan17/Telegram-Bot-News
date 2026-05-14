"""
Centralized configuration for the Telegram News Bot.
All magic numbers and retention policies belong here.
"""

# Retention Policies
NEWS_RETENTION_DAYS = 15
COMMAND_LOG_RETENTION_DAYS = 7

# Dashboard / Health Monitoring
CRON_INTERVAL_MIN = 15

# Dynamic thresholds based on interval
# Warn after 2 missed runs (30m), Error after 8 missed runs (2h)
CRON_WARN_THRESHOLD_MIN = CRON_INTERVAL_MIN * 2
CRON_ERR_THRESHOLD_MIN = CRON_INTERVAL_MIN * 8


# Scoring / Filtering
MIN_NEWS_SCORE = 4
