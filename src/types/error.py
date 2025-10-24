class error(Exception):
    def __init__(self, message: str = None):
        self.message = message
        super().__init__(message)

    def string(self) -> str:
        return self.message


class httpError(error):
    def __init__(self, code: int, message: str = None):
        self.code = code
        super().__init__(message)


type Error = error | httpError | None
