from .wastuff import sync_service, async_service, wasbase

class AsyncWAS (wasbase.WASBase, async_service.AsyncService):
    pass
WAS = AsyncWAS

class SyncWAS (wasbase.WASBase, sync_service.SyncService):
    pass
        


