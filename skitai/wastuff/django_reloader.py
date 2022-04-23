class DjangoReloader:
    def __init__ (self, mounted, logger):
        from django.utils import autoreload

        self.mounted = mounted
        self.logger = logger
        self.mtimes = {}
        self.version = 1
        if hasattr (autoreload, "code_changed"):
            self.reloader = autoreload
        else:
            self.version = 2
            self.reloader = autoreload.get_reloader ()

    def reloaded (self):
        if self.version == 1:
            return self.reloader.code_changed ()
        else:
            for filepath, mtime in self.reloader.snapshot_files ():
                if not str (filepath).startswith (self.mounted):
                    continue
                old_time = self.mtimes.get (filepath)
                self.mtimes [filepath] = mtime
                if old_time is None:
                    continue
                elif mtime > old_time:
                    return True
        return False
