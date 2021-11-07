from pymongo import auth, message, helpers
import pytest
from bson.son import SON
from bson.codec_options import CodecOptions
from rs4.protocols.dbi import asynmongo
import struct
import bson
import sys

def test_pymongo ():
    response = b"%s%s%s%s%s" %  (
        struct.pack ("<i", 4),
        struct.pack ("<q", 1),
        struct.pack ("<i", 1),
        struct.pack ("<i", 1),
        bson.BSON.encode ({"hello": "world"})
    )
    assert asynmongo._unpack_response (response, 1) == {'starting_from': 1, 'number_returned': 1, 'cursor_id': 1, 'data': [{'hello': 'world'}]}

    payload = bson.BSON.encode ({"hello": "world"})
    response = b"%s%s%s" %  (
        struct.pack ("<B", 0),
        struct.pack ("<i", len (payload)),
        payload
    )
    assert asynmongo._unpack_response (response, 2013) == {'first_payload_type': 0, 'data': [{'hello': 'world'}], 'first_payload_size': 22}

    if '__pypy__' in sys.builtin_module_names:
        opts = CodecOptions (SON)
        assert auth._auth_key (1, "a", "b") == "90b38d5dbfabd0b883e17ae67847220a"
        assert message.query(0, "%s.$cmd" % "mydb", 0, 1, SON({'getnonce': 1}), SON({}), opts) [-1] == 19
        assert message.query (0, "col.a", 0, 1, {"_id": 1}, None, opts) [-1] == 14
        assert message.update ("col.a", 0, 0, {"_id": 1}, {"a": 1}, 1, (), False, opts) [-1] == 12

        msg = message.delete ("col.a", {"_id": 1}, 1, (), opts, 0)
        assert len (msg) == 3 and msg [-1] == 14

        msg = message.insert ("col.a", [{"a": 1}], False, 1, (), 0, opts)
        assert len (msg) == 3 and msg [-1] == 12

    else:
        opts = CodecOptions (SON)
        assert auth._auth_key (1, "a", "b") == "90b38d5dbfabd0b883e17ae67847220a"
        assert message.query(0, "%s.$cmd" % "mydb", 0, 1, SON({'getnonce': 1}), SON({}), opts) == (
            1804289383, b'>\x00\x00\x00gE\x8bk\x00\x00\x00\x00\xd4\x07\x00\x00\x00\x00\x00\x00mydb.$cmd\x00\x00\x00\x00\x00\x01\x00\x00\x00\x13\x00\x00\x00\x10getnonce\x00\x01\x00\x00\x00\x00\x05\x00\x00\x00\x00', 19
        )
        assert message.query (0, "col.a", 0, 1, {"_id": 1}, None, opts) == (
            846930886, b'0\x00\x00\x00\xc6#{2\x00\x00\x00\x00\xd4\x07\x00\x00\x00\x00\x00\x00col.a\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0e\x00\x00\x00\x10_id\x00\x01\x00\x00\x00\x00', 14
        )
        assert message.update ("col.a", 0, 0, {"_id": 1}, {"a": 1}, 1, (), False, opts) == (
            1681692777, b'8\x00\x00\x00i\x98<d\x00\x00\x00\x00\xd1\x07\x00\x00\x00\x00\x00\x00col.a\x00\x00\x00\x00\x00\x0e\x00\x00\x00\x10_id\x00\x01\x00\x00\x00\x00\x0c\x00\x00\x00\x10a\x00\x01\x00\x00\x00\x00<\x00\x00\x00i\x98<d\x00\x00\x00\x00\xd4\x07\x00\x00\x00\x00\x00\x00col.$cmd\x00\x00\x00\x00\x00\xff\xff\xff\xff\x17\x00\x00\x00\x10getlasterror\x00\x01\x00\x00\x00\x00', 14
        )

        msg = message.delete ("col.a", {"_id": 1}, 1, (), opts, 0)
        assert len (msg) == 3 and msg [0] == 1714636915 and msg [-1] == 14

        msg = message.insert ("col.a", [{"a": 1}], False, 1, (), 0, opts)
        assert len (msg) == 3 and msg [0] == 1957747793 and msg [-1] == 12