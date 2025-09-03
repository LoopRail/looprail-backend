class error(Exception):
    def __init__(self, message: str = None):
        self.message = message
        super().__init__(message)

    def string(self) -> str:
        return self.message


type Error = error | None
