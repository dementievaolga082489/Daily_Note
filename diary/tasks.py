"""Celery-задачи приложения diary (отправка в MAX)."""

import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone

from diary.models import Entry, Reminder
from users.models import MaxProfile

logger = get_task_logger(__name__)


@shared_task
def send_max_message(max_user_id: str, text: str) -> bool:
    """Отправляет текстовое сообщение в MAX (или имитирует отправку, если нет токена)."""

    # ★ ЕСЛИ ТОКЕНА НЕТ — ИМИТИРУЕМ ОТПРАВКУ
    if not settings.MAX_BOT_TOKEN:
        logger.info("=" * 50)
        logger.info("📨 [ИМИТАЦИЯ ОТПРАВКИ В MAX]")
        logger.info("Кому (max_user_id): %s", max_user_id)
        logger.info("Текст:\n%s", text)
        logger.info("=" * 50)
        return True  # Возвращаем True, чтобы задачи считали, что отправка успешна

    # Если токен есть — реальный запрос к API MAX
    url = f"{settings.MAX_API_URL}/messages"
    headers = {
        "Authorization": f"Bearer {settings.MAX_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {"user_id": max_user_id},
        "text": text
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.ok:
            return True
        logger.error("MAX API error: %s %s", resp.status_code, resp.text)
        return False
    except requests.RequestException as exc:
        logger.exception("Ошибка при отправке в MAX: %s", exc)
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
        profile = MaxProfile.objects.filter(user=entry.author).first()
        if not profile or not profile.max_user_id:
            continue

        text = f"🔔 *Напоминание (дневник)*\n\n*{entry.title or 'Без названия'}*\n\n{entry.content[:300]}"

        if send_max_message(profile.max_user_id, text):
            entry.reminder_sent = True
            entry.save(update_fields=["reminder_sent"])
            sent_count += 1

    logger.info("Entry-напоминаний обработано: %s", sent_count)
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
        profile = MaxProfile.objects.filter(user=r.author).first()
        if not profile or not profile.max_user_id:
            continue

        text = f"📅 *Напоминание из календаря*\n\n*{r.title}*\n\n{r.description[:300]}"

        if send_max_message(profile.max_user_id, text):
            r.sent = True
            r.save(update_fields=["sent"])
            sent_count += 1

    logger.info("Reminder-напоминаний обработано: %s", sent_count)
    return sent_count