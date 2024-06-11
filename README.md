# BotX-SmartApp-RPC
Библиотека, позволяющая писать смартаппы, используя [наш JSONRPC-like протокол](https://ccsteam.atlassian.net/wiki/spaces/EI/pages/193167368/SmartApp+RPC)

## Установка
Используя `poetry`:

```bash
poetry add pybotx-smartapp-rpc
```

## Добавление RPC методов
1. Создайте класс для входящих аргументов:
``` python
from pybotx_smartap_rpc import RPCArgsBaseModel
...
class SumArgs(RPCArgsBaseModel):
    a: int
    b: int
```
2. Создайте RPC метод:
``` python
from pybotx_smartapp_rpc import SmartApp, RPCRouter, RPCResultResponse
...
rpc = RPCRouter()
...
@rpc.method("sum")
async def sum(
    smartapp: SmartApp, rpc_arguments: SumArgs
) -> RPCResultResponse[int]:
    return RPCResultResponse(result=rpc_arguments.a + rpc_arguments.b)

# Так же у метода может не быть аргументов:
@rpc.method("answer")
async def answer(smartapp: SmartApp) -> RPCResultResponse[int]:
    return RPCResultResponse(result=42)
```
3. Создайте экземпляр `SmartAppRPC` и подключите роутер из прошлого пункта:
``` python
from pybotx_smartapp_rpc import SmartAppRPC

from anywhere import methods 
...
smartapp = SmartAppRPC(routers=[methods.rpc])
```
4. Сделайте хендлер для `smartapp_event` и вызывайте в нем хендлер библиотеки:  
    a. Aсинхронный подход:
    ``` python
    @collector.smartapp_event
    async def handle_smartapp_event(event: SmartAppEvent, bot: Bot) -> None:
        await smartapp.handle_smartapp_event(event, bot)
    ```
   б. Синхронный подход:
    ``` python
   from pybotx import SyncSmartAppEventResponsePayload
   
   ...
   
    @collector.sync_smartapp_event
    async def handle_sync_smartapp_event(event: SmartAppEvent, bot: Bot) -> SyncSmartAppEventResponsePayload:
        return await smartapp.handle_sync_smartapp_event(event, bot)
    ```

## Продвинутая работа с библиотекой
* В `RPCResultResponse` можно передавать `botx.File` файлы.
``` python
@rpc.method("get-pdf")
async def get_pdf(
    smartapp: SmartApp, rpc_arguments: GetPDFArgs
) -> RPCResultResponse[None]:
    ...
    return RPCResultResponse(result=None, files=[...])
```
* В `SmartAppRPC`, `RPCRouter` и `RPCRouter.method` можно передать мидлвари, сначала будут вызваны мидлвари приложения, затем мидлвари роутера и в конце мидлвари метода.
``` python
smartapp = SmartAppRPC(..., middlewares=[...])
...
rpc = RPCRouter(middlewares=[...])
...
@rpc.method("sum", middlewares=[...])
```
* `RPCArgsBaseModel` это алиас для `pydantic.BaseModel`, вы можете использовать все возможности исходного класса.
``` python
from uuid import UUID
...
class DelUserArgs(RPCArgsBaseModel):
    # pydantic сериализует входящую строку в UUID
    user_huid: UUID
```
* Через объект `smartapp`, передаваемый в хендлер можно получить доступ к `event` и `bot`.
``` python
...
@rpc.method("del-user")
async def del_user(
    smartapp: SmartApp, rpc_arguments: DelUserArgs
) -> RPCResultResponse[None]:
    await smartapp.bot.send_message(
        body="Done",
        bot_id=smartapp.event.bot.id,
        chat_id=smartapp.event.chat.id,
    )
    ...
```
* Используя метод `smartapp.send_event` можно отправлять RPC ивенты с `ref: null`.  
Это может пригодиться при необходимости отправки уведомления не в ответ на RPC запрос.
``` python
@rpc.method("notify-me")
async def notify_me(
    smartapp: SmartApp, rpc_arguments: NotifyMeArgs
) -> RPCResultResponse[None]:
    ...
    await smartapp.send_event("notified", files=[notify_file])
    ...
```
* Используя метод `smartapp.send_push` или `smartapp.send_custom_push` можно отправлять пуш уведомлений на клиент.
И обновлять счетчик уведомлений на икноке смартапа.
``` python
@rpc.method("notify-me")
async def notify_me(
    smartapp: SmartApp, rpc_arguments: NotifyMeArgs
) -> RPCResultResponse[None]:
    await smartapp.send_push(42, "You have 42 new emails!")
    ...
```
* В мидлварях можно создавать новые объекты в `smartapp.state`, чтобы потом использовать их в хендлерах.
``` python
async def user_middleware(smartapp: SmartApp, rpc_arguments: RPCArgsBaseModel, call_next: Callable) -> RPCResponse[User]:
    smartapp.state.user = await User.get(smartapp.message.user_huid)
    return await call_next(smartapp, rpc_arguments)

@rpc.method("get-user-fullname")
async def get_user_fullname(smartapp: SmartApp) -> RPCResultResponse[str]:
    return RPCResultResponse(result=smartapp.state.user.fullname)
```
* Можно выбрасывать пользовательские RPC ошибки, которые будут отправлены как ответ на RPC запрос.
``` python
from pybotx_smartapp_rpc import RPCErrorExc, RPCError

class CustomError(RPCError):
    id = "CUSTOM_ERROR"
    reason = "It's error reason"

...
@rpc.method("return-error")
async def return_error(smartapp: SmartApp, rpc_arguments: RaiseOneErrorArgs) -> None:
    # one error
    raise RPCErrorExc(
        CustomError(
            meta={"args": rpc_arguments.dict()},
        )
    )
    # or list of errors
    raise RPCErrorExc(
        [
            CustomError(
                meta={"args": rpc_arguments.dict()},
            ),
            RPCError(
                reason="It's one more error reason",
                id="CUSTOM_ERROR_NUMBER_TWO",
                meta={"args": rpc_arguments.dict()},
            )
        ]
    )
```
* Можно добавить хендлер на определенный тип исключений. В него будут отправлять исключения того же и дочерних классов.
Хендлер **обязан** возвращать `RPCErrorResponse`, ошибки из которого будут отправлены источнику запроса.
``` python
from pybotx_smartapp_rpc import SmartAppRPC, RPCErrorResponse
...
async def key_error_handler(exc: KeyError, smartapp: SmartApp) -> RPCErrorResponse:
    key = exc.args[0]
    return RPCErrorResponse(
        errors=[
            RPCError(
                reason=f"Key {key} not found.",
                id="KEY_ERROR",
                meta={"key": key},
            ),
        ]
    )

smartapp = SmartAppRPC(..., exception_handlers={KeyError: key_error_handler})
```

### Swagger documentation
Можно подключить rpc роутеры к авто генерируемой документации FastAPI и использовать
документацию в Swagger. Для этого необходимо переопределить функцию для генерации 
OpenAPI схемы:
```python
from fastapi import FastAPI

application = FastAPI()
def get_custom_openapi():
    return custom_openapi(
        title="Smartapp API",
        version="0.1.0",
        fastapi_routes=application.routes,
        rpc_router=smartapp.router,
        openapi_version="3.0.2",
    )

application.openapi = get_custom_openapi
```

Пример функции `custom_openapi`:
```python
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.models import OpenAPI
from fastapi.openapi.utils import get_openapi
from pybotx_smartapp_rpc import RPCRouter
from pybotx_smartapp_rpc.openapi_utils import *
from pydantic.schema import get_model_name_map
from starlette.routing import BaseRoute


def custom_openapi(
    *,
    title: str,
    version: str,
    fastapi_routes: Sequence[BaseRoute],
    rpc_router: RPCRouter,
    **kwargs: Any,
) -> Dict[str, Any]:
    openapi_dict = get_openapi(
        title=title,
        version=version,
        routes=fastapi_routes,
        **kwargs,
    )

    paths: Dict[str, Dict[str, Any]] = {}

    flat_rpc_models = get_rpc_flat_models_from_routes(rpc_router)
    rpc_model_name_map = get_model_name_map(flat_rpc_models)
    rpc_definitions = get_rpc_model_definitions(
        flat_models=flat_rpc_models, model_name_map=rpc_model_name_map
    )

    for method_name in rpc_router.rpc_methods.keys():
        if not rpc_router.rpc_methods[method_name].include_in_schema:
            continue

        path = get_rpc_openapi_path(  # type: ignore
            method_name=method_name,
            route=rpc_router.rpc_methods[method_name],
            model_name_map=rpc_model_name_map,
        )
        if path:
            paths.setdefault(f"/{method_name}", {}).update(path)

    if rpc_definitions:
        openapi_dict.setdefault("components", {}).setdefault("schemas", {}).update(
            {k: rpc_definitions[k] for k in sorted(rpc_definitions)}
        )

    openapi_dict.setdefault("paths", {}).update(paths)

    return jsonable_encoder(OpenAPI(**openapi_dict), by_alias=True, exclude_none=True)
```
### Возможности RPC Swagger

* Можно добавлять теги к запросам, анaлогично FastAPI.
``` python
rpc = RPCRouter(tags=["RPC"])

@rpc.method("documented-method", tags=["docs"])
async def docs(
    smartapp: SmartApp, rpc_arguments: DocumentedArgs
) -> RPCResultResponse[DocumentedResponse]:
    """Desctiption of this method."""
    ...
```
* Можно переопределять pydantic модель успешного ответа.
``` python
@rpc.method("method", return_type=Response)
async def method(
    smartapp: SmartApp, rpc_arguments: MethodArgs
) -> RPCResultResponse[int]:
    ...
```
* Можно исключать некоторые методы из документации.
``` python
rpc = RPCRouter(include_in_schema=False)

@rpc.method("_hidden_method", include_in_schema=False)
async def hidden_method(smartapp: SmartApp) -> RPCResultResponse[int]:
    ...
```
* Можно определять пользовательские ошибки.
``` python
from pybotx_smartapp_rpc import RPCError, RPCErrorExc

class Meta(BaseModel):
    user_id: int
    username: str


class UsernotFoundError(RPCError):
    """Error description for swagger."""
    id = "UserNotFound"
    reason = "User not found in db"
    meta: Meta


@rpc.method("method-with_error", errors=[UsernotFoundError])
async def get_user(
    smartapp: SmartApp, rpc_arguments: UserArgs
) -> RPCResultResponse[User]:
    ...
    raise RPCErrorExc(UsernotFoundError(meta={"user_id": 1, "username": "test"}))
```
