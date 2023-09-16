from modules.base_module import Module
import modules.notify as notify

class_name = "Income"


class Income(Module):
    prefix = "isin"
    
    def __init__(self, server):
        self.server = server
        self.commands = {"ben": self.buy_energy}
    
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
