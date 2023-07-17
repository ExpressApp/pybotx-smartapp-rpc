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
4. Сделайте хендлер для `smartapp_event` и вызывайте в нем хендлер библиотеки
``` python
@collector.smartapp_event
async def handle_smartapp_event(event: SmartAppEvent, bot: Bot) -> None:
    await smartapp.handle_smartapp_event(event, bot)
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
* Используя метод `smartapp.send_push` можно отправлять пуш уведомлений на клиент.
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
...
@rpc.method("return-error")
async def return_error(smartapp: SmartApp, rpc_arguments: RaiseOneErrorArgs) -> None:
    # one error
    raise RPCErrorExc(
        RPCError(
            reason="It's error reason",
            id="CUSTOM_ERROR",
            meta={"args": rpc_arguments.dict()},
        )
    )
    # or list of errors
    raise RPCErrorExc(
        [
            RPCError(
                reason="It's error reason",
                id="CUSTOM_ERROR",
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
    )

application.openapi = get_custom_openapi
```

Пример функции `custom_openapi`:
```python
from fastapi import routing
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.models import OpenAPI
from fastapi.openapi.utils import get_flat_models_from_routes, get_openapi_path
from fastapi.utils import get_model_definitions

def custom_openapi(
    *,
    title: str,
    version: str,
    openapi_version: str = "3.0.2",
    description: Optional[str] = None,
    fastapi_routes: Sequence[BaseRoute],
    rpc_router: RPCRouter,
    tags: Optional[List[Dict[str, Any]]] = None,
    servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
    terms_of_service: Optional[str] = None,
    contact: Optional[Dict[str, Union[str, Any]]] = None,
    license_info: Optional[Dict[str, Union[str, Any]]] = None,
) -> Dict[str, Any]:
    info: Dict[str, Any] = {"title": title, "version": version}
    if description:
        info["description"] = description
    if terms_of_service:
        info["termsOfService"] = terms_of_service
    if contact:
        info["contact"] = contact
    if license_info:
        info["license"] = license_info
        
    output: Dict[str, Any] = {"openapi": openapi_version, "info": info}
    if servers:
        output["servers"] = servers
        
    components: Dict[str, Dict[str, Any]] = {}
    paths: Dict[str, Dict[str, Any]] = {}
    # FastAPI
    flat_fastapi_models = get_flat_models_from_routes(fastapi_routes)
    fastapi_model_name_map = get_model_name_map(flat_fastapi_models)
    fast_api_definitions = get_model_definitions(
        flat_models=flat_fastapi_models, model_name_map=fastapi_model_name_map
    )

    # pybotx RPC
    flat_rpc_models = get_rpc_flat_models_from_routes(rpc_router)
    rpc_model_name_map = get_model_name_map(flat_rpc_models)
    rpc_definitions = get_model_definitions(
        flat_models=flat_rpc_models, model_name_map=rpc_model_name_map
    )

    for route in fastapi_routes:
        if isinstance(route, routing.APIRoute):
            result = get_openapi_path(
                route=route, model_name_map=fastapi_model_name_map
            )
            if result:
                path, security_schemes, path_definitions = result
                if path:
                    paths.setdefault(route.path_format, {}).update(path)
                if security_schemes:
                    components.setdefault("securitySchemes", {}).update(
                        security_schemes
                    )
                if path_definitions:
                    fast_api_definitions.update(path_definitions)

    for method_name in rpc_router.rpc_methods.keys():
        if not rpc_router.rpc_methods[method_name].include_in_schema:
            continue

        result = get_rpc_openapi_path(
            method_name=method_name,
            route=rpc_router.rpc_methods[method_name],
            model_name_map=rpc_model_name_map,
        )
        if result:
            path, path_definitions = result
            if path:
                paths.setdefault(method_name, {}).update(path)

            if path_definitions:
                rpc_definitions.update(path_definitions)

    if fast_api_definitions:
        components["schemas"] = {
            k: fast_api_definitions[k] for k in sorted(fast_api_definitions)
        }
    if rpc_definitions:
        components.setdefault("schemas", {}).update(
            {k: rpc_definitions[k] for k in sorted(rpc_definitions)}
        )
    if components:
        output["components"] = components
    
    output["paths"] = paths
    if tags:
        output["tags"] = tags

    return jsonable_encoder(OpenAPI(**output), by_alias=True, exclude_none=True)  # type: ignore
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
