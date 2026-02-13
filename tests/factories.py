import factory
from faker import Faker

from pybotx_smartapp_rpc.models.request import RPCRequest

_faker = Faker("en_US")
Faker.seed(20260213)


class RPCRequestFactory(factory.Factory):
    class Meta:
        model = RPCRequest

    method = factory.LazyFunction(lambda: _faker.lexify(text="method_????"))
    type = "smartapp_rpc"
    params = factory.LazyFunction(
        lambda: {"value": _faker.pyint(min_value=1, max_value=100)},
    )
