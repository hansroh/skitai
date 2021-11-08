from django.db import models
from atila.patches.djangopatch import Model

class User (Model):
    uid = models.CharField (max_length = 32)
    email = models.EmailField (max_length = 64, null = True, blank = True)
    email_verified = models.BooleanField (default = False, blank = True)
    nick_name = models.CharField (max_length = 16, null = True, blank = True)
    signature = models.CharField (max_length = 64, null = True, blank = True)
    salt = models.CharField (max_length = 24, null = True, blank = True)

    phone_no = models.CharField (max_length = 32, null = True, blank = True)
    photo_url = models.TextField (null = True, blank = True)
    provider = models.CharField (max_length = 32, null = True, blank = True)
    name = models.CharField (max_length = 32, null = True, blank = True)
    gender = models.CharField (max_length = 8, null = True, blank = True)
    birthday = models.CharField (max_length = 16, null = True, blank = True)

    grp = models.CharField (max_length = 16, default = 'user', choices = [('guest', 'guest'), ('user', 'user'), ('staff', 'staff'), ('admin', 'admin')])
    status = models.CharField (max_length = 16, null = True, blank = True)
    created = models.DateTimeField (auto_now_add = True)
    last_updated = models.DateTimeField (auto_now = True)

    class Meta:
        proxy = False
        managed = True
        db_table = 'firebase_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__ (self):
        return '{}'.format (self.nick_name)


class UserLog (Model):
    user = models.ForeignKey (User, models.CASCADE)
    action = models.CharField (max_length = 16)
    payload = models.JSONField (null = True, blank = True)
    created = models.DateTimeField (auto_now_add = True)

    class Meta:
        proxy = False
        managed = True
        db_table = 'firebase_user_log'
        verbose_name = 'User Log'
        verbose_name_plural = 'User Logs'

    def __str__ (self):
        return '{}'.format (self.user)
