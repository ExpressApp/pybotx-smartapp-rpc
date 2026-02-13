from pybotx_smartapp_rpc.models.errors import RPCError


class BaseRPCErrorExc(Exception): ...  # noqa: WPS428, WPS604, E701


class RPCErrorExc(BaseRPCErrorExc):
    def __init__(self, error_or_errors: RPCError | list[RPCError]):
        if isinstance(error_or_errors, RPCError):
            self.errors = [error_or_errors]
        else:
            self.errors = error_or_errors
