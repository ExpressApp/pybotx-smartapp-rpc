from typing import List, Union

from pybotx_smartapp_rpc.models.errors import RPCError


class BaseRPCErrorExc(Exception): ...  # noqa: N818


class RPCErrorExc(BaseRPCErrorExc):  # noqa: N818
    def __init__(self, error_or_errors: Union[RPCError, List[RPCError]]):
        if isinstance(error_or_errors, RPCError):
            self.errors = [error_or_errors]
        else:
            self.errors = error_or_errors
