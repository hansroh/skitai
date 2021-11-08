import os
import sys
import pytest
from django.core.exceptions import ValidationError
from skitai.exceptions import HTTPError
import datetime

def test_service_layer (wasc, service_layer):
    from dap.transcription.services import TranscriptionService
    assert not TranscriptionService.get (1).fetch ()
    with pytest.raises (ValidationError):
        TranscriptionService.add (1, {'id': 1}).commit ()

    with pytest.raises (ValidationError):
        TranscriptionService.add (1, {'creted': datetime.datetime.now ()}).commit ()

    with pytest.raises (ValidationError):
        TranscriptionService.add (1, {'last_update': datetime.datetime.now ()}).commit ()

    with pytest.raises (ValidationError):
        TranscriptionService.add (1, {'video_url': 'URL', 'callback_uri': 'URL'}).commit ()

    with pytest.raises (ValidationError):
        TranscriptionService.add (1, {'id': 1, 'video_uri': 'URL', 'callback_uri': 'URL', 'upload_path': 'URL'}).commit ()

    with pytest.raises (ValidationError):
        TranscriptionService.add (1, {'last_update': datetime.datetime.now (), 'video_uri': 'URL', 'callback_uri': 'URL', 'upload_path': 'URL'}).commit ()

    TranscriptionService.add (1, {'video_uri': 'URL', 'callback_uri': 'URL', 'upload_path': 'URL'}).commit ()
    task = TranscriptionService.get (1).one ()
    assert task ['task_id'] == 1

    with pytest.raises (ValidationError):
        TranscriptionService.update (1, {'status': 'processing2'}).commit ()

    TranscriptionService.update (1, {'status': 'processing'}).commit ()
    task = TranscriptionService.get (1).one ()
    assert task ['last_status'] == 'processing'

    tasks = TranscriptionService.find ('processing').fetch ()
    assert tasks [0]['last_status'] == 'processing'

    logs = TranscriptionService.get_logs (1).fetch ()
    assert logs [0]['transcription_id'] == task.task_id
    assert logs [0]['status'] == 'processing'

    TranscriptionService.remove (1).commit ()
    assert not TranscriptionService.get (1).fetch ()
    assert not TranscriptionService.get_logs (1).fetch ()
