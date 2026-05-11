"""Backward-compatible persistence facade.

The bot imports this module directly today. Keep these functions stable while the
actual persistence implementation moves behind repository adapters.
"""

from bot.repositories.factory import create_repository
from bot.repositories.supabase_repository import create_supabase_client

supabase = create_supabase_client()
_repository_override = None
_repository_instance = None


def set_repository(repository) -> None:
    """Override persistence implementation, mainly for tests or future adapters."""
    global _repository_override
    _repository_override = repository


def clear_repository_override() -> None:
    global _repository_override
    _repository_override = None


def reset_repository() -> None:
    """Force lazy repository recreation after environment changes."""
    global _repository_instance
    _repository_instance = None


def _repository():
    global _repository_instance
    if _repository_override is not None:
        return _repository_override
    if _repository_instance is None:
        _repository_instance = create_repository(supabase_client=supabase)
    return _repository_instance


def get_all_users() -> list:
    return _repository().get_all_users()


def add_user(chat_id: int) -> dict:
    return _repository().add_user(chat_id)


def set_news_enabled(chat_id: int, enabled: bool) -> str:
    return _repository().set_news_enabled(chat_id, enabled)


def get_user_timezone(chat_id: int) -> str:
    return _repository().get_user_timezone(chat_id)


def set_user_timezone(chat_id: int, tz_string: str) -> bool:
    return _repository().set_user_timezone(chat_id, tz_string)


def get_news_subscribers() -> list:
    return _repository().get_news_subscribers()


def is_news_sent(news_hash: str) -> bool:
    return _repository().is_news_sent(news_hash)


def mark_news_sent(news_hash: str) -> bool:
    return _repository().mark_news_sent(news_hash)


def get_user_stats() -> dict:
    return _repository().get_user_stats()


def ban_user(chat_id: int) -> str:
    return _repository().ban_user(chat_id)


def log_command(chat_id: int, command: str) -> None:
    return _repository().log_command(chat_id, command)


def update_bot_health(status: str = "ok") -> None:
    return _repository().update_bot_health(status)


def get_dashboard_stats() -> dict:
    return _repository().get_dashboard_stats()
