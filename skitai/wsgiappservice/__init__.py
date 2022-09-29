from . import wasbase, deprecated
from .wastype import _WASType

class WAS (wasbase.WASBase, deprecated.Deprecated):
    def __init__ (self, **options):
        self.options = options
