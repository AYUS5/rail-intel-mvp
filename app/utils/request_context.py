from contextvars import ContextVar
from uuid import uuid4


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str:
    request_id = request_id_var.get()
    if request_id:
        return request_id
    request_id = str(uuid4())
    request_id_var.set(request_id)
    return request_id


def set_request_id(request_id: str) -> None:
    request_id_var.set(request_id)
