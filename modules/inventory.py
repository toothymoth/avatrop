from modules.base_module import Module
import modules.notify as notify
import time

class_name = "Inventory"


class Inventory(Module):
    prefix = "isin"
    
    def __init__(self, server):
        self.server = server
        self.dailyGifts = self.server.parser.parse_daily_gift()
        self.res = self.server.parser.parse_resources()
        self.commands = {"dg": self.getDailyGift,
                         "shdgd": self._showDailyGiftDialog,
                         "sale": self.sale}
    
    async def _showDailyGiftDialog(self, client):
        r = self.server.redis
        if await r.incrby(f"uid:{client.uid}:dailyTime", 0) - int(time.time()) <= 0:
            day = await r.incrby(f"uid:{client.uid}:dailyDay", 0) + 1
            # await r.incrby(f"uid:{client.uid}:dailyTime", int(time.time())+24*60*60)
            await client.send(["isin.dg", {'d': day}])
            
    async def sale(self, msg, client):
        r = self.server.redis
        count = msg[2]["cnt"]
        item = msg[2]["tpid"]
        if 0 < count < 50:
            if not await self.server.inv[client.uid].take_item(item, count):
                return
            await r.incrby(f"uid:{client.uid}:slvr", self.res[item]["saleSilver"]*count)
            await notify.update_resources(client, self.server)
            inv = self.server.inv[client.uid].get()
            await client.send(["ntf.invch", {"inv": inv}])
            
    async def getDailyGift(self, msg, client):
        r = self.server.redis
        day = await r.incrby(f"uid:{client.uid}:dailyDay", 0) + 1
        if day not in self.dailyGifts:
            return
        gift = self.dailyGifts[day]  # itemType="game" or "resource" itemId="" count=""
        if gift["itemType"] == "game":
            await self.server.inv[client.uid].add_item(gift["itemId"], "res", int(gift["count"]))
            inv = self.server.inv[client.uid].get()
            await client.send(["ntf.invch", {"inv": inv}])
        elif gift["itemType"] == "resource":
            nameRes = _removeVowels(gift["itemId"])
            await r.incrby(f"uid:{client.uid}:{nameRes}", gift["count"])
            await notify.update_resources(client, self.server)
        if await r.incrby(f"uid:{client.uid}:dailyDay", 1) == 30:
            await r.set(f"uid:{client.uid}:dailyDay", 0)
        await r.incrby(f"uid:{client.uid}:dailyTime", int(time.time()) + 24 * 60 * 60)


def _removeVowels(string):
    vowels = ["e", "y", "u", "i", "o", "a"]
    new_string = string
    for i in vowels:
        new_string = new_string.lower().replace(i, "")
    return new_string
