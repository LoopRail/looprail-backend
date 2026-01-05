class error(Exception):
    def __init__(self, message: str = None):
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message

    def __eq__(self, value: object, /) -> bool:
        return self.message == value

    def __ne__(self, value: object, /) -> bool:
        return self.message != value


class httpError(error):
    def __init__(self, code: int, message: str = None):
        self.code = code
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.message} {self.code}"


class UpdatingProtectedFieldError(error):
    def __init__(self, field: str = None):
        super().__init__(f"updating protected field: {field}")



class FailedAttemptError(error):
    def __init__(self, message: str = "Failed attempt"):
        super().__init__(message)


class InvalidCredentialsError(error):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


NotFoundError = error("not found")
ProtectedModelError = error("protected model can't update")
ItemDoesNotExistError = error("item does not exist")
type Error = error | httpError | None
