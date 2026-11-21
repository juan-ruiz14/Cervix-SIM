"""Errores tipificados (CE-07): el frontend recibe siempre {error: {code, message}}."""


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra
