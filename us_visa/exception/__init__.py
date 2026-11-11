from types import ModuleType


def error_message_detail(error: BaseException | str, error_detail: ModuleType) -> str:
    """Build a human-readable message from an exception and its traceback.

    ``error_detail`` is normally the ``sys`` module, which is how every call site
    in this project passes it.
    """
    _, _, exc_tb = error_detail.exc_info()

    if exc_tb is None:
        return f"Error occurred: {error}"

    file_name = exc_tb.tb_frame.f_code.co_filename
    return (
        f"Error occurred python script name [{file_name}] "
        f"line number [{exc_tb.tb_lineno}] error message [{error}]"
    )


class USvisaException(Exception):
    """Project-specific exception that always carries file/line context."""

    def __init__(self, error_message: BaseException | str, error_detail: ModuleType) -> None:
        """
        :param error_message: exception or message describing the failure
        :param error_detail: ``sys`` module, used to inspect the active traceback
        """
        super().__init__(error_message)
        self.error_message = error_message_detail(error_message, error_detail=error_detail)

    def __str__(self) -> str:
        return self.error_message
