class ImporterError(Exception):
    """An actionable error safe to display without credentials or HTTP payloads."""


class InputError(ImporterError):
    pass


class PlaylistConflict(ImporterError):
    """A conflict that may be recoverable after reading the destination."""

    def __init__(self, message: str, *, reported_duplicate: bool = False):
        super().__init__(message)
        self.reported_duplicate = reported_duplicate
