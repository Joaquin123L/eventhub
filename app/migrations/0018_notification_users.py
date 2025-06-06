# Generated by Django 5.2.1 on 2025-05-18 16:33

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0017_remove_notification_read_remove_notification_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='users',
            field=models.ManyToManyField(related_name='notifications', through='app.NotificationUser', to=settings.AUTH_USER_MODEL),
        ),
    ]
