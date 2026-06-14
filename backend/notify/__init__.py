"""Notificaciones push (Telegram). Ver telegram.py."""
from .telegram import configured, notify_alerts, send

__all__ = ["configured", "notify_alerts", "send"]
