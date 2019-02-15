from redis import connection as redisconn
from redis.exceptions import DataError
import pytest

def test_redis ():
    redis = redisconn.Connection ()
    
    assert redis.pack_command ("PUSH", "someting") == [b'*2\r\n$4\r\nPUSH\r\n$8\r\nsometing\r\n']
    assert redis.pack_command ("PUSH", 1) == [b'*2\r\n$4\r\nPUSH\r\n$1\r\n1\r\n']
    with pytest.raises (DataError):
        redis.pack_command ("PUSH", [1])
    
    
    
    