class DomainError(Exception):
    pass


class EmptyStorageError(DomainError):
    pass


class InvalidTextError(DomainError):
    pass


class InvalidVectorError(DomainError):
    pass
