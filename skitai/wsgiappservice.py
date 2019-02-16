from .wastuff import sync_service, async_service, wasbase
from .wastuff import semaps

class AsyncWAS (wasbase.WASBase, async_service.AsyncService):
    pass
WAS = AsyncWAS

class SyncWAS (wasbase.WASBase, sync_service.SyncService):
    pass
        
class TestWAS (SyncWAS):
    numthreads = 1 
    _luwatcher = semaps.TestSemaps ()
    _stwatcher = semaps.TestSemaps ()

