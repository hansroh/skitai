import os
import sys

def test_services (wasc, service_layer):
    from dap.transcription.services import TranscriptionService

    print (TranscriptionService.get (1).fetch ())