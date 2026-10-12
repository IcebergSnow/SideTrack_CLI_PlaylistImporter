class ImporterError(Exception):
    """An actionable error safe to display without credentials or HTTP payloads."""


class InputError(ImporterError):
    pass
