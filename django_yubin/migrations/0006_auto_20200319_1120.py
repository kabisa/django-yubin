# Generated by Django 2.2.11 on 2020-03-19 16:20

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('django_yubin', '0005_auto_20181128_0407'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='blacklist',
            options={'ordering': ('-date_added',), 'verbose_name': 'blacklisted email', 'verbose_name_plural': 'blacklisted emails'},
        ),
        migrations.AlterModelOptions(
            name='log',
            options={'ordering': ('-date',), 'verbose_name': 'log', 'verbose_name_plural': 'logs'},
        ),
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ('date_created',), 'verbose_name': 'message', 'verbose_name_plural': 'messages'},
        ),
        migrations.AddField(
            model_name='log',
            name='action',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Created'), (1, 'Queued'), (2, 'In process'), (3, 'Sent'), (4, 'Failed'), (5, 'Blacklisted'), (6, 'Discarded')], default=0, verbose_name='action'),
        ),
        migrations.AddField(
            model_name='message',
            name='date_enqueued',
            field=models.DateTimeField(blank=True, null=True, verbose_name='date enqueued'),
        ),
        migrations.AddField(
            model_name='message',
            name='enqueued_count',
            field=models.PositiveSmallIntegerField(default=0, help_text='Times the message has been enqueued', verbose_name='enqueued count'),
        ),
        migrations.AddField(
            model_name='message',
            name='sent_count',
            field=models.PositiveSmallIntegerField(default=0, help_text='Times the message has been sent', verbose_name='sent count'),
        ),
        migrations.AddField(
            model_name='message',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Created'), (1, 'Queued'), (2, 'In process'), (3, 'Sent'), (4, 'Failed'), (5, 'Blacklisted'), (6, 'Discarded')], default=0),
        ),
        migrations.AlterField(
            model_name='blacklist',
            name='date_added',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='date added'),
        ),
        migrations.AlterField(
            model_name='blacklist',
            name='email',
            field=models.EmailField(max_length=200, verbose_name='email'),
        ),
        migrations.AlterField(
            model_name='log',
            name='date',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='date'),
        ),
        migrations.AlterField(
            model_name='log',
            name='log_message',
            field=models.TextField(blank=True, verbose_name='log'),
        ),
        migrations.AlterField(
            model_name='log',
            name='message',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='django_yubin.Message', verbose_name='message'),
        ),
        migrations.AlterField(
            model_name='log',
            name='result',
            field=models.PositiveSmallIntegerField(choices=[(0, 'success'), (1, 'not sent (blacklisted or paused)'), (2, 'failure')], help_text='Deprecated for new emails, see "action"', null=True),
        ),
        migrations.AlterField(
            model_name='message',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True, verbose_name='date created'),
        ),
        migrations.AlterField(
            model_name='message',
            name='date_sent',
            field=models.DateTimeField(blank=True, null=True, verbose_name='date sent'),
        ),
        migrations.AlterField(
            model_name='message',
            name='encoded_message',
            field=models.TextField(verbose_name='encoded message'),
        ),
        migrations.AlterField(
            model_name='message',
            name='from_address',
            field=models.CharField(max_length=200, verbose_name='from address'),
        ),
        migrations.AlterField(
            model_name='message',
            name='subject',
            field=models.CharField(max_length=255, verbose_name='subject'),
        ),
        migrations.AlterField(
            model_name='message',
            name='to_address',
            field=models.CharField(max_length=200, verbose_name='to address'),
        ),
    ]
