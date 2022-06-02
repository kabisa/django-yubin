import datetime
import logging

from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.db import models
from django.db.models import F
from django.utils.encoding import force_bytes
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from kombu.exceptions import KombuError
import mailparser

from . import message_utils, tasks


logger = logging.getLogger(__name__)


class MessageQuerySet(models.QuerySet):
    def queueable(self):
        return self.filter(status__in=self.model.QUEUEABLE_STATUSES)

    def retryable(self, max_retries=0):
        qs = self.filter(status__gt=self.model.STATUS_SENT)
        if max_retries > 0:
            qs = qs.filter(enqueued_count__lt=max_retries)
        return qs


class MessageManager(models.Manager):
    def get_queryset(self):
        return MessageQuerySet(self.model, using=self._db)

    def queueable(self):
        return self.get_queryset().queueable()

    def retryable(self, max_retries=0):
        return self.get_queryset().retryable(max_retries=max_retries)


class Message(models.Model):
    """
    An email message.

    The ``to_address``, ``from_address`` and ``subject`` fields are merely for
    easy of access for these common values. The ``encoded_message`` field
    contains the entire encoded email message ready to be sent to an SMTP
    connection.
    """
    STATUS_CREATED = 0
    STATUS_QUEUED = 1
    STATUS_IN_PROCESS = 2
    STATUS_SENT = 3
    STATUS_FAILED = 4
    STATUS_BLACKLISTED = 5
    STATUS_DISCARDED = 6
    STATUS_CHOICES = (
        (STATUS_CREATED, _('Created')),
        (STATUS_QUEUED, _('Queued')),
        (STATUS_IN_PROCESS, _('In process')),
        (STATUS_SENT, _('Sent')),
        (STATUS_FAILED, _('Failed')),
        (STATUS_BLACKLISTED, _('Blacklisted')),
        (STATUS_DISCARDED, _('Discarded')),
    )
    QUEUEABLE_STATUSES = (STATUS_CREATED, STATUS_FAILED, STATUS_BLACKLISTED, STATUS_DISCARDED)
    SENDABLE_STATUSES = (*QUEUEABLE_STATUSES, STATUS_QUEUED)

    to_address = models.CharField(_('to address'), max_length=200)
    from_address = models.CharField(_('from address'), max_length=200)
    subject = models.CharField(_('subject'), max_length=255)

    encoded_message = models.TextField(_('encoded message'))
    date_created = models.DateTimeField(_('date created'), auto_now_add=True)

    date_sent = models.DateTimeField(_('date sent'), null=True, blank=True)
    sent_count = models.PositiveSmallIntegerField(_('sent count'), default=0,
                                                  help_text=_('Times the message has been sent'))

    date_enqueued = models.DateTimeField(_('date enqueued'), null=True, blank=True)
    enqueued_count = models.PositiveSmallIntegerField(_('enqueued count'), default=0,
                                                      help_text=_('Times the message has been enqueued'))

    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=STATUS_CREATED)

    objects = MessageManager()

    class Meta:
        ordering = ('date_created',)
        verbose_name = _('message')
        verbose_name_plural = _('messages')

    def __str__(self):
        return '%s: %s' % (self.to_address, self.subject)

    def can_be_sent(self):
        return self.status in self.SENDABLE_STATUSES

    def mark_as(self, status, log_message=None):
        self.status = status
        if status is self.STATUS_SENT:
            self.date_sent = now()
            self.sent_count = F('sent_count') + 1
        elif status is self.STATUS_QUEUED:
            self.date_enqueued = now()
            self.enqueued_count = F('enqueued_count') + 1
        self.save()
        if log_message:
            self.add_log(log_message)

    def get_message(self):
        try:
            msg = mailparser.parse_from_string(self.encoded_message)
        except UnicodeEncodeError:
            msg = mailparser.parse_from_string(force_bytes(self.encoded_message))
        except (TypeError, AttributeError):
            msg = mailparser.parse_from_bytes(self.encoded_message)
        return msg

    def get_email_message(self):
        """
        Returns EmailMultiAlternatives or EmailMessage depending on whether the email is multipart or not.
        """
        msg = self.get_message()

        Email = EmailMultiAlternatives if msg.text_html else EmailMessage
        email = Email(
            subject=msg.subject,
            body='\n'.join(msg.text_plain),
            from_email=message_utils.get_address(msg.from_),
            to=message_utils.get_addresses(msg.to),
            cc=message_utils.get_addresses(msg.cc),
            bcc=message_utils.get_addresses(msg.bcc),
        )

        if msg.text_html:
            email.attach_alternative('<br>'.join(msg.text_html), mimetype='text/html')

        for attachment in message_utils.get_attachments(msg):
            email.attach(attachment.filename, attachment.payload, attachment.type)

        return email

    def add_log(self, log_message):
        Log.objects.create(message=self, action=self.status, log_message=log_message)

    @classmethod
    def delete_old(cls, days=90):
        """
        Deletes mails created before `days` days.

        Returns the deletion data from Django and the cuttoff date.
        """
        cutoff_date = now() - datetime.timedelta(days)
        deleted = cls.objects.filter(date_created__lt=cutoff_date).delete()
        return deleted, cutoff_date

    def enqueue(self, log_message=None):
        """
        Sends the task to enqueue itself taking care of undoing changes if the delivery fails.
        """
        backup = {
            'date_enqueued': self.date_enqueued,
            'enqueued_count': self.enqueued_count,
            'status': self.status,
        }
        self.mark_as(self.STATUS_QUEUED, log_message)
        try:
            tasks.send_email.delay(self.pk)
        except KombuError:
            self.date_enqueued = backup['date_enqueued']
            self.enqueued_count = backup['enqueued_count']
            self.status = backup['status']
            self.save()
            self.add_log('Error enqueuing email.')
            raise


class Blacklist(models.Model):
    """
    A blacklisted email address.

    Messages attempted to be sent to e-mail addresses which appear on this
    blacklist will be skipped entirely.
    """
    email = models.EmailField(_('email'), max_length=200)
    date_added = models.DateTimeField(_('date added'), default=now)

    class Meta:
        ordering = ('-date_added',)
        verbose_name = _('blacklisted email')
        verbose_name_plural = _('blacklisted emails')

    def __str__(self):
        return self.email


class Log(models.Model):
    """
    A log used to record the activity of a queued message.
    """
    message = models.ForeignKey(Message, verbose_name=_('message'), editable=False, on_delete=models.CASCADE)
    action = models.PositiveSmallIntegerField(_('action'), choices=Message.STATUS_CHOICES,
                                              default=Message.STATUS_CREATED)
    date = models.DateTimeField(_('date'), auto_now_add=True)
    log_message = models.TextField(_('log'), blank=True)

    class Meta:
        ordering = ('-date',)
        verbose_name = _('log')
        verbose_name_plural = _('logs')
