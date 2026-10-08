class DomainError(Exception):
    pass


class InvalidUploadError(DomainError):
    pass


class UnsupportedFormatError(InvalidUploadError):
    pass


class FileTooLargeError(InvalidUploadError):
    pass


class EmptyContentError(InvalidUploadError):
    pass


class AuditFailedError(DomainError):
    pass