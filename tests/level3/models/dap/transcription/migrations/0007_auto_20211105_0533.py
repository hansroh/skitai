# Generated by Django 3.2.9 on 2021-11-05 05:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcription', '0006_auto_20211105_0532'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transcription',
            name='callback_uri',
            field=models.CharField(max_length=1024),
        ),
        migrations.AlterField(
            model_name='transcription',
            name='video_uri',
            field=models.CharField(max_length=1024),
        ),
    ]
