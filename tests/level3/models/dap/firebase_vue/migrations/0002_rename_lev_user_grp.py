# Generated by Django 3.2 on 2021-11-04 01:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('firebase_vue', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='lev',
            new_name='grp',
        ),
    ]
