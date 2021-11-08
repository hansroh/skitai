from skitai import was
from .models import Transcription, TranscriptionLog

class TranscriptionService:
    @classmethod
    def get_transcription_id (self, task_id):
        return Transcription.get (task_id = task_id).partial ("id")

    @classmethod
    def find (cls, status):
        return Transcription.get (last_status = status).execute ()

    @classmethod
    def get (cls, task_id):
        return Transcription.get (task_id = task_id).execute ()

    @classmethod
    def get_logs (cls, task_id):
        return TranscriptionLog.get (transcription_id = cls.get_transcription_id (task_id)).execute ()

    @classmethod
    def add (cls, task_id, payload):
        payload ['task_id'] = task_id
        return Transcription.add (payload).execute ()

    @classmethod
    def remove (cls, task_id):
        with Transcription.transaction () as db:
            TranscriptionLog.remove (transcription_id = cls.get_transcription_id (task_id)).execute ()
            Transcription.remove (task_id = task_id).execute ()
            return db.commit ()

    @classmethod
    def update (cls, task_id, payload):
        with Transcription.transaction () as db:
            Transcription.set (dict (last_status = payload ['status'])).filter (task_id = task_id).execute ()
            payload ['transcription_id'] = cls.get_transcription_id (task_id)
            TranscriptionLog.add (payload).execute ()
            return db.commit ()

