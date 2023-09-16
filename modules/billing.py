from modules.base_module import Module
import modules.notify as notify

class_name = "Billing"


class Billing(Module):
    prefix = "b"
    
    def __init__(self, server):
        self.server = server
        self.commands = {"chkprchs": self.check_purchase,
                         "bs": self.buy_silver, "ren": self.buy_energy}
    
    async def check_purchase(self, msg, client):
        amount = int(msg[2]["prid"].split("pack")[1])
        user_data = await self.server.get_user_data(client.uid)
        gold = user_data["gld"] + amount
        await self.server.redis.set(f"uid:{client.uid}:gld", gold)
        await self.server.redis.set(f"uid:{client.uid}:act",
                                    user_data["act"] + 1)
        await client.send(["acmr.adac", {"vl": 1}])
        await notify.update_resources(client, self.server)
        await client.send(["b.ingld", {"ingld": amount}])
    
    async def buy_energy(self, msg, client):
        if int(await self.server.redis.get(f"uid:{client.uid}:gld")) < 3:
            return
        await self.server.redis.set(f"uid:{client.uid}:enrg", 100)
        await self.server.redis.incrby(f"uid:{client.uid}:act", 1)
        await self.server.redis.decrby(f"uid:{client.uid}:gld", 3)
        await client.send(["acmr.adac", {"vl": 1}])
        await notify.update_resources(client, self.server)
        msg.pop(0)
        await client.send(msg)
    
    async def buy_silver(self, msg, client):
        user_data = await self.server.get_user_data(client.uid)
        if user_data["gld"] < msg[2]["gld"]:
            return
        await self.server.redis.set(f"uid:{client.uid}:gld",
                                    user_data["gld"] - msg[2]["gld"])
        await self.server.redis.set(f"uid:{client.uid}:slvr",
                                    user_data["slvr"] + msg[2]["gld"] * 100)
        await notify.update_resources(client, self.server)
        await client.send(["b.inslv", {"inslv": msg[2]["gld"] * 100}])
