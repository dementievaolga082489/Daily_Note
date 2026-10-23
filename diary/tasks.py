"""Celery-задачи приложения diary."""

import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone

from diary.models import Entry, Reminder
from users.models import TelegramProfile

logger = get_task_logger(__name__)


@shared_task
def send_telegram_message(chat_id: str, text: str) -> bool:
    """Отправляет текстовое сообщение в Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN не задан — отправка невозможна")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        if resp.ok:
            return True
        logger.error("Telegram API error: %s %s", resp.status_code, resp.text)
        return False
    except requests.RequestException as exc:
        logger.exception("Ошибка при отправке в Telegram: %s", exc)
        return False


@shared_task
def check_and_send_entry_reminders() -> int:
    """Напоминания по записям дневника (Entry.reminder_at)."""
    now = timezone.now()
    entries = Entry.objects.filter(
        reminder_at__lte=now, reminder_sent=False,
    ).select_related("author")

    sent_count = 0
    for entry in entries:
        profile = TelegramProfile.objects.filter(user=entry.author).first()
        if not profile or not profile.chat_id:
            continue
        text = f"🔔 *Напоминание (дневник)*\n\n*{entry.title}*\n\n{entry.content[:300]}"
        if send_telegram_message(profile.chat_id, text):
            entry.reminder_sent = True
            entry.save(update_fields=["reminder_sent"])
            sent_count += 1
    logger.info("Entry-напоминаний отправлено: %s", sent_count)
    return sent_count


@shared_task
def check_and_send_calendar_reminders() -> int:
    """Напоминания из календаря (Reminder.remind_at)."""
    now = timezone.now()
    reminders = Reminder.objects.filter(
        remind_at__lte=now, sent=False,
    ).select_related("author")

    sent_count = 0
    for r in reminders:
        profile = TelegramProfile.objects.filter(user=r.author).first()
        if not profile or not profile.chat_id:
            continue
        text = f"📅 *Напоминание из календаря*\n\n*{r.title}*\n\n{r.description[:300]}"
        if send_telegram_message(profile.chat_id, text):
            r.sent = True
            r.save(update_fields=["sent"])
            sent_count += 1
    logger.info("Reminder-напоминаний отправлено: %s", sent_count)
    return sent_count