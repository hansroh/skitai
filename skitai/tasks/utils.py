import ctypes
from rs4.protocols.sock.impl.grpc.producers import serialize as grpc_serialize
from rs4.protocols.sock.impl.ws.collector import encode_message
from rs4.protocols.sock.impl.ws import *

WAS_FACTORY = None

def determine_response_type (request):
    if request.get_header ("upgrade") == 'websocket':
        return 'websocket'
    elif request.get_header ("content-type", "").startswith ('application/grpc'):
        return 'grpc'

def serialize (rtype, v):
    if not v:
        return v
    if rtype is None:
        return v
    if rtype == 'grpc':
        return grpc_serialize (v, True)
    if rtype == 'websocket':
        if isinstance (v, tuple):
            opcode, v =  v
        else:
            opcode = OPCODE_TEXT if isinstance (v, str) else OPCODE_BINARY
        return encode_message (v, opcode)

def deceive_context (was, coro):
    from skitai.wsgiappservice.wastype import _WASType

    for n, v in coro.cr_frame.f_locals.items ():
        if not isinstance (v, _WASType):
            continue
        coro.cr_frame.f_locals [n] = was
    ctypes.pythonapi.PyFrame_LocalsToFast (ctypes.py_object (coro.cr_frame), ctypes.c_int (0))

def get_cloned_context (was_id):
    global WAS_FACTORY

    assert was_id, 'was.ID should be non-zero'
    if WAS_FACTORY is None:
        import skitai
        WAS_FACTORY = skitai.was

    _was = WAS_FACTORY._get_by_id (was_id)
    assert hasattr (_was, 'app'), 'Task future is available on only Atila'

    if isinstance (was_id, int): # origin
        return _was._clone ()
    return _was
