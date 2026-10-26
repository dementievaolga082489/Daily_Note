"""Celery-задачи приложения diary (отправка на Email)."""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from diary.models import Entry, Reminder

logger = get_task_logger(__name__)


@shared_task
def send_email_notification(to_email: str, subject: str, text: str) -> bool:
    """Отправляет email-сообщение."""
    if not to_email:
        logger.warning("У пользователя не указан email — отправка невозможна")
        return False

    try:
        send_mail(
            subject=subject,
            message=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.exception("Ошибка при отправке email: %s", exc)
        return False


@shared_task
def check_and_send_entry_reminders() -> int:
    """Напоминания по записям дневника (Entry.reminder_at)."""
    now = timezone.now()
    entries = Entry.objects.filter(
        reminder_at__lte=now,
        reminder_sent=False,
    ).select_related("author")

    sent_count = 0
    for entry in entries:
        if not entry.author.email:
            continue

        subject = f"🔔 Напоминание: {entry.title or 'Запись в дневнике'}"
        text = (
            f"Привет, {entry.author.username}!\n\n"
            f"Напоминание по записи:\n\n"
            f"Заголовок: {entry.title or 'Без названия'}\n"
            f"Дата: {entry.date}\n\n"
            f"Содержание:\n{entry.content[:500]}\n\n"
            f"---\n"
            f"Это автоматическое сообщение, отвечать на него не нужно."
        )

        if send_email_notification(entry.author.email, subject, text):
            entry.reminder_sent = True
            entry.save(update_fields=["reminder_sent"])
            sent_count += 1

    logger.info("Entry-напоминаний отправлено на email: %s", sent_count)
    return sent_count


@shared_task
def check_and_send_calendar_reminders() -> int:
    """Напоминания из календаря (Reminder.remind_at)."""
    now = timezone.now()
    reminders = Reminder.objects.filter(
        remind_at__lte=now,
        sent=False,
    ).select_related("author")

    sent_count = 0
    for r in reminders:
        if not r.author.email:
            continue

        subject = f"📅 Напоминание: {r.title}"
        text = (
            f"Привет, {r.author.username}!\n\n"
            f"Напоминание из календаря:\n\n"
            f"Событие: {r.title}\n"
            f"Время: {r.remind_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Описание:\n{r.description or 'Без описания'}\n\n"
            f"---\n"
            f"Это автоматическое сообщение, отвечать на него не нужно."
        )

        if send_email_notification(r.author.email, subject, text):
            r.sent = True
            r.save(update_fields=["sent"])
            sent_count += 1

    logger.info("Reminder-напоминаний отправлено на email: %s", sent_count)
    return sent_count
