#!/usr/bin/env python
# encoding: utf-8
# ----------------------------------------------------------------------------

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.encoding import force_bytes
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from mailparser import parse_from_string, parse_from_bytes
from six import python_2_unicode_compatible

from django_yubin import constants, managers


PRIORITIES = (
    (constants.PRIORITY_NOW, 'now'),
    (constants.PRIORITY_HIGH, 'high'),
    (constants.PRIORITY_NORMAL, 'normal'),
    (constants.PRIORITY_LOW, 'low'),
)

RESULT_CODES = (
    (constants.RESULT_SENT, 'success'),
    (constants.RESULT_SKIPPED, 'not sent (blacklisted or paused)'),
    (constants.RESULT_FAILED, 'failure'),
)


@python_2_unicode_compatible
class Message(models.Model):
    """
    An email message.

    The ``to_address``, ``from_address`` and ``subject`` fields are merely for
    easy of access for these common values. The ``encoded_message`` field
    contains the entire encoded email message ready to be sent to an SMTP
    connection.

    """
    to_address = models.CharField(max_length=200)
    from_address = models.CharField(max_length=200)

    cc_recipients = ArrayField(
        models.EmailField(), verbose_name=_("CC"), blank=True, null=True
    )

    bcc_recipients = ArrayField(
        models.EmailField(), verbose_name=_("BCC"), blank=True, null=True
    )

    subject = models.CharField(max_length=255)

    encoded_message = models.TextField()
    date_created = models.DateTimeField(default=now)
    date_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('date_created',)

    def __str__(self):
        return '%s: %s' % (self.to_address, self.subject)

    def save(self, **kwargs):
        cc_recipients = self.cc_recipients or []
        bcc_recipients = self.bcc_recipients or []

        self.cc_recipients = list(
            set(self._parse_cc_recipients()) | set(cc_recipients)
        )

        self.bcc_recipients = list(
            set(self._parse_bcc_recipients()) | set(bcc_recipients)
        )

        super().save(**kwargs)

    def get_mailparser_message(self):
        try:
            return parse_from_string(self.encoded_message)
        except UnicodeEncodeError:
            return parse_from_string(force_bytes(self.encoded_message))
        except (TypeError, AttributeError):
            return parse_from_bytes(self.encoded_message)

    def get_message(self):
        mailparser_message = self.get_mailparser_message()
        return mailparser_message.message

    def _parse_bcc_recipients(self):
        message = self.get_message()

        return [
            recipient.strip()
            for recipient in message.get("Bcc", "").split(",")
            if recipient.strip()
        ]

    def _parse_cc_recipients(self):
        message = self.get_message()

        return [
            recipient.strip()
            for recipient in message.get("Cc", "").split(",")
            if recipient.strip()
        ]

    def get_cc_recipients_display(self):
        return ",".join(self.cc_recipients) if self.cc_recipients else ""

    def get_bcc_recipients_display(self):
        return ",".join(self.bcc_recipients) if self.bcc_recipients else ""


class QueuedMessage(models.Model):
    """
    A queued message.

    Messages in the queue can be prioritised so that the higher priority
    messages are sent first (secondarily sorted by the oldest message).

    """
    message = models.OneToOneField(Message, editable=False, on_delete=models.CASCADE)
    priority = models.PositiveSmallIntegerField(choices=PRIORITIES,
                                                default=constants.PRIORITY_NORMAL)
    deferred = models.DateTimeField(null=True, blank=True)
    retries = models.PositiveIntegerField(default=0)
    date_queued = models.DateTimeField(default=now)

    objects = managers.QueueManager()

    class Meta:
        ordering = ('priority', 'date_queued')

    def defer(self):
        self.deferred = now()
        self.save()


class Blacklist(models.Model):
    """
    A blacklisted email address.

    Messages attempted to be sent to e-mail addresses which appear on this
    blacklist will be skipped entirely.

    """
    email = models.EmailField(max_length=200)
    date_added = models.DateTimeField(default=now)

    class Meta:
        ordering = ('-date_added',)
        verbose_name = 'blacklisted e-mail address'
        verbose_name_plural = 'blacklisted e-mail addresses'


class Log(models.Model):
    """
    A log used to record the activity of a queued message.

    """
    message = models.ForeignKey(Message, editable=False, on_delete=models.CASCADE)
    result = models.PositiveSmallIntegerField(choices=RESULT_CODES)
    date = models.DateTimeField(default=now)
    log_message = models.TextField()

    class Meta:
        ordering = ('-date',)
