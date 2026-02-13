from pybotx_smartapp_rpc.models.errors import RPCError


class BaseRPCErrorExc(Exception):
    pass


class RPCErrorExc(BaseRPCErrorExc):
    def __init__(self, error_or_errors: RPCError | list[RPCError]):
        if isinstance(error_or_errors, RPCError):
            self.errors = [error_or_errors]
        else:
            self.errors = error_or_errors
