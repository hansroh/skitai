# Generated by Django 3.2.9 on 2021-11-05 05:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcription', '0003_auto_20211105_0525'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transcription',
            name='callback_url',
            field=models.CharField(max_length=1024),
        ),
        migrations.AlterField(
            model_name='transcription',
            name='video_url',
            field=models.CharField(max_length=1024),
        ),
    ]
