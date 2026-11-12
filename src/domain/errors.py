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


class UserAlreadyExistsError(DomainError):
    pass


class InvalidStructureError(DomainError):
    pass


class CVNotFoundError(DomainError):
    pass


class CVNotReadyError(DomainError):
    pass


class CVProcessingError(DomainError):
    def __init__(self, error_code: str, error_message: str) -> None:
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message


class CVFailedError(CVProcessingError):
    pass


class StorageError(DomainError):
    pass
