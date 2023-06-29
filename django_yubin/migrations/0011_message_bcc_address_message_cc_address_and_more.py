# Generated by Django 4.2 on 2023-05-03 07:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("django_yubin", "0010_message_storage")]

    operations = [
        migrations.AddField(
            model_name="message",
            name="bcc_address",
            field=models.TextField(
                blank=True, default="", verbose_name="bcc addresses"
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="cc_address",
            field=models.TextField(blank=True, default="", verbose_name="cc addresses"),
        ),
        migrations.AlterField(
            model_name="message",
            name="to_address",
            field=models.TextField(verbose_name="to addresses"),
        ),
    ]
