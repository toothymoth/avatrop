from modules.base_module import Module
from modules.location import get_island_info
import const
import time

class_name = "Passport"


class Passport(Module):
    prefix = "psp"

    def __init__(self, server):
        self.server = server
        self.commands = {"sttrph": self.set_trophy, "psp": self.passport,
                         "stpsrtdcr": self.set_pass_decor, "pspdl": self.pspdl, "pspdr": self.pspdr}
        self.help_cooldown = {}

    async def set_trophy(self, msg, client):
        user_data = await self.server.get_user_data(client.uid)
        if msg[2]["trid"] not in const.trophies:
            await self.server.redis.delete(f"uid:{client.uid}:trid")
            trid = None
        else:
            trid = msg[2]["trid"]
            if trid in const.PREMIUM_TROPHIES:
                if not user_data["premium"]:
                    return
            if trid in const.BLACKLIST_TROPHIES:
                return
            await self.server.redis.set(f"uid:{client.uid}:trid", trid)
        await client.send(["psp.sttrph", {"trid": trid}])
        ci = await get_island_info(client.uid, self.server)
        await client.send(["ntf.ci", {"ci": ci}])

    async def pspdl(self, msg, client):
        redis = self.server.redis
        getDl = await redis.get(f"pspdl:{client.uid}")
        if getDl:
            await client.send(["psp.pspdl", {"dl": True}])
            await redis.delete(f"pspdl:{client.uid}")
        elif not getDl:
            await client.send(["psp.pspdl", {"dl": False}])
            await redis.set(f"pspdl:{client.uid}", 1)
        ci = await get_island_info(client.uid, self.server)
        await client.send(["ntf.ci", {"ci": ci}])
        return

    async def pspdr(self, msg, client):
        redis = self.server.redis
        getDr = await redis.get(f"pspdr:{client.uid}")
        if getDr:
            await client.send(["psp.pspdr", {"dr": True}])
            await redis.delete(f"pspdr:{client.uid}")
        elif not getDr:
            await client.send(["psp.pspdr", {"dr": False}])
            await redis.set(f"pspdr:{client.uid}", 1)
        ci = await get_island_info(client.uid, self.server)
        await client.send(["ntf.ci", {"ci": ci}])
        return

    async def passport(self, msg, client):
        ac = {}
        self.achievements = await self.server.redis.lrange(f"achievements:{msg[2]['uid']}", 0, -1)
        self.trophies = await self.server.redis.lrange(f"trophies:{msg[2]['uid']}", 0, -1)
        for item in self.achievements:
            ac[item] = {"p": 0, "nWct": 0, "l": 3, "aId": item}
        tr = {}
        user_data = await self.server.get_user_data(msg[2]["uid"])
        for item in self.trophies:
            if item in const.PREMIUM_TROPHIES:
                if not user_data["premium"]:
                    continue
            if item in const.BLACKLIST_TROPHIES:
                continue
            tr[item] = {"trrt": 0, "trcd": 0, "trid": item}
        rel = {}
        rl = self.server.modules["rl"]
        r = self.server.redis
        relations = await r.smembers(f"rl:{msg[2]['uid']}")
        for link in relations:
            relation = await rl._get_relation(msg[2]["uid"], link)
            if not relation:
                continue
            if relation["rlt"]["s"] // 10 in [6, 7]:
                uid = relation["uid"]
                rel[uid] = relation["rlt"]
        await client.send(["psp.psp", {"psp": {"uid": msg[2]["uid"],
                                               "ach": {"ac": ac, "tr": tr},
                                               "rel": rel}}])

    async def set_pass_decor(self, msg, client):
        psrtdcr = msg[2]["psrtdcr"]
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 5:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        await self.server.redis.set(f"uid:{client.uid}:psrtdcr", psrtdcr)
        await client.send(["psp.stpsrtdcr", {"psrtdcr": psrtdcr}])
        ci = await get_island_info(client.uid, self.server)
        await client.send(["ntf.ci", {"ci": ci}])
