from modules.base_module import Module
import modules.notify as notify
from modules.location import refresh_avatar, gen_plr, get_island_info

class_name = "Shop"


class Shop(Module):
    prefix = "issh"

    def __init__(self, server):
        self.server = server
        
        self.commands = {"bsi": self.buy_game_item}

    async def buy_game_item(self, msg, client):
        item = msg[2]["tpid"]
        cnt = msg[2]["cnt"]
        if await self.buy(client, item, count=cnt):
            await client.send(msg[1:])

    async def buy(self, client, item, count=1):
        if item in self.server.food:
            type_ = "fd"
        elif item in self.server.med:
            type_ = "med"
        else:
            await self.server._______________________________________________________________________________(client, "shop off")
            return False
        await self.server.inv[client.uid].add_item(item, type_, count)
        inv = self.server.inv[client.uid].get()
        await client.send(["ntf.invch", {"inv": inv}])
        return True
