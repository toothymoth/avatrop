import traceback, const
from modules.base_module import Module

class_name = "Component"


class Component(Module):
    prefix = "cp"

    def __init__(self, server):
        self.server = server
        self.commands = {"cht": self.chat, "m": self.moderation}

    async def chat(self, msg, client):
        subcommand = msg[1].split(".")[2]
        if subcommand == "sm":  # send message
            msg.pop(0)
            if msg[1]["msg"]["cid"]:
                for uid in msg[1]["msg"]["cid"].split("_"):
                    if uid in self.server.online:
                        await self.server.online[uid].send(msg)
            else:
                if "msg" in msg[1]["msg"]:
                    message = msg[1]["msg"]["msg"]
                    if len(message) < 250:
                        if message.startswith("!"):
                            try:
                                return await self.system_command(message, client)
                            except Exception:
                                print(traceback.format_exc())
                                msg = "Ошибка в синтаксисе команды, проверьте правильность"
                                return await client.send(["cp.ms.rsm", {"txt": msg}])
                msg[1]["msg"]["sid"] = client.uid
                online = self.server.online
                room = self.server.rooms[client.room]
                room = list(set(room)) # removing repeat's players
                for uid in room:
                    try:
                        tmp = online[uid]
                    except KeyError:
                        room.remove(uid)
                        continue
                    await tmp.send(msg)

    async def inval_msg(self, msg):
        is_english = False
        for word in msg:
            if 97 <= ord(word) <= 122:
                is_english = True
                break
        return is_english

    async def moderation(self, msg, client):
        subcommand = msg[1].split(".")[2]
        if subcommand == "ar":  # access request
            user_data = await self.server.get_user_data(client.uid)
            if user_data["role"] >= const.privileges[msg[2]["pvlg"]]:
                success = True
            else:
                success = False
            await client.send(["cp.m.ar", {"pvlg": msg[2]["pvlg"],
                                           "sccss": success}])

    async def system_command(self, msg, client):
        command = msg[1:]
        if " " in command:
            command = command.split(" ")[0]
        elif command == "ssm":
            await self.send_system_message(msg, client)
        else:
            await client.send(["cp.ms.rsm", {"txt": f"Команда {command} не найдена"}])

    async def send_system_message(self, msg, client):
        user_data = await self.server.get_user_data(client.uid)
        if user_data["role"] < 5:
            return await self.no_permission(client)
        message = msg.split(f"!cmd ")[1]
        online = self.server.online
        for uid in self.server.online:
            await online[uid].send(["cp.ms.rsm", {"txt": message}])

    async def no_permission(self, client):
        await client.send(["cp.ms.rsm", {"txt": "У вас недостаточно прав, "
                                                "чтобы выполнить эту "
                                                "команду"}])
