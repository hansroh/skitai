from django.db import models
from atila.patches.djangopatch import Model

STATUS = [
    ('pending', 'pending'), ('processing', 'processing'),
    ('completed', 'completed'), ('failed', 'failed')
]

class Transcription (Model):
    task_id = models.IntegerField ()
    video_uri = models.CharField (max_length = 1024)
    callback_uri = models.CharField (max_length = 1024)
    upload_path = models.CharField (max_length = 1024)
    last_status = models.CharField (max_length = 16, default = 'pending', choices = STATUS)
    created = models.DateTimeField (auto_now_add = True)
    last_updated = models.DateTimeField (auto_now = True)

    class Meta:
        proxy = False
        managed = True
        db_table = 'transcription'
        verbose_name = 'Transcription'
        verbose_name_plural = 'Transcriptions'

    def __str__ (self):
        return '{}'.format (self.task_id)


class TranscriptionLog (Model):
    transcription = models.ForeignKey (Transcription, models.CASCADE)
    status  = models.CharField (max_length = 16, choices = STATUS)
    reason  = models.CharField (max_length = 512, null = True, blank = True)
    created = models.DateTimeField (auto_now_add = True)

    class Meta:
        proxy = False
        managed = True
        db_table = 'transcription_log'
        verbose_name = 'Transcription Log'
        verbose_name_plural = 'Transcription Logs'
