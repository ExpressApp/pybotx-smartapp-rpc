# BotX-SmartApp-RPC
Библиотека, позволяющая писать смартаппы, используя [наш JSONRPC-like протокол](https://ccsteam.atlassian.net/wiki/spaces/EI/pages/193167368/SmartApp+RPC)

## Установка
В `pyproject.toml`:
1. Переключите `pybotx` на ветку `next`:
`botx = { git = "https://github.com/ExpressApp/pybotx.git", rev = "next" }`
2. Добавьте зависимость:
`botx-smartapp-rpc = { git = "https://gitlab.ccsteam.ru/rnd/botx-smartapp-rpc", rev = "master" }`

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
