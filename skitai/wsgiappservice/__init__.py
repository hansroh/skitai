from . import async_service, wasbase, deprecated
from .wastype import _WASType

class WAS (wasbase.WASBase, deprecated.Deprecated):
    pass

class AsyncServicableWAS (WAS, async_service.AsyncService):
    # with async services
    pass
