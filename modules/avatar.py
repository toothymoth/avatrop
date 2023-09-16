import json
import logging
from modules.location import refresh_avatar
from modules.base_module import Module
from inventory import Inventory
from modules.notify import update_resources

class_name = "Avatar"

with open("modules/default_map.json", "r") as f:
    defMap = json.load(f)


class Avatar(Module):
    prefix = "a"
    
    def __init__(self, server):
        self.server = server
        self.clothes_list = self.server.parser.parse_category_clothes()
        self.sets = self.server.parser.parse_clothes_sets()
        self.commands = {"apprnc": self.appearance, "clths": self.clothes}
    
    async def appearance(self, msg, client):
        subcommand = msg[1].split(".")[2]
        if subcommand == "rnn":
            name = msg[2]["unm"].strip()
            if not name:
                return
            await self.server.redis.lset(f"uid:{client.uid}:appearance",
                                         0, name)
            user_data = await self.server.get_user_data(client.uid)
            await client.send(["a.apprnc.rnn",
                               {"res": {"slvr": user_data["slvr"],
                                        "enrg": user_data["enrg"],
                                        "emd": user_data["emd"],
                                        "gld": user_data["gld"]},
                                "unm": name}])
        elif subcommand == "save":
            apprnc = msg[2]["apprnc"]
            current_apprnc = await self.server.get_appearance(client.uid)
            if not current_apprnc:
                await self.update_appearance(apprnc, client)
                self.server.inv[client.uid] = Inventory(self.server,
                                                        client.uid)
                await self.server.inv[client.uid]._get_inventory()
                await self.server.redis.set(f"uid:{client.uid}:wearing",
                                            "casual")
                if int(apprnc["g"]) == 1:
                    # boys
                    clothes = ["bShrt1", "bPnts1", "bShs1"]
                elif int(apprnc["g"]) == 2:
                    # girls
                    clothes = ["gShrt1", "gPnts1", "gShs1", "gBrlt1", "gNckls1"]
                for cl in clothes:
                    await self.server.inv[client.uid].add_item(cl, "cts", 1)
                    await self.server.inv[client.uid].change_wearing(cl, True)
                await self.create_map(client)
            else:
                if apprnc["g"] != current_apprnc["g"]:
                    logging.info("gender doesn't match!")
                    return
            await self.update_appearance(apprnc, client)
            await client.send(["a.apprnc.save", {"apprnc": apprnc}])
    
    async def create_map(self, client):
        r = self.server.redis
        uid = client.uid
        for catMap in ["ws", "pts", "t", "b", "dc", "np"]:
            for item in defMap[catMap]:
                if not item:
                    continue
                if "id" not in item:
                    continue
                await r.rpush(f"uid:{uid}:islandMap:{catMap}", item['id'])
                for arg in list(item.keys()):
                    if item[arg] is None:
                        await r.set(f"uid:{uid}:islandMap:{catMap}:{item['id']}:{arg}", "None")
                    else:
                        await r.set(f"uid:{uid}:islandMap:{catMap}:{item['id']}:{arg}", item[arg])
    
    async def clothes(self, msg, client):
        subcommand = msg[1].split(".")[2]
        if subcommand == "wear":
            await self.wear_cloth(msg, client)
        elif subcommand == "buy":
            clothes = [{"tpid": msg[2]["tpid"], "clid": ""}]
            await self.buy_clothes(msg[1], clothes, client)
        elif subcommand in ["bcc", "bac"]:
            await self.buy_clothes(msg[1], msg[2]["clths"],
                                   client)
        elif subcommand == "bst":
            await self.buy_clothes_suit(msg[2]["tpid"],
                                        client)
        else:
            logging.warning(f"Command {msg[1]} not found")
    
    async def change_ctp(self, uid, new_ctp):
        ctp = await self.server.redis.get(f"uid:{uid}:wearing")
        if ctp == new_ctp:
            return
        await self.server.redis.set(f"uid:{uid}:wearing", new_ctp)
        await self.server.inv[uid]._get_inventory()
    
    async def wear_cloth(self, msg, client):
        """["ntf.invch", {inv: {
            c: {bld: {it: [], id: "bld"}, its: {it: [], id: "its"}, sds: {it: [], id: "sds"}, dec: {it: [], id: "dec"},
                fd: {it: [{atr: {bt: 1685947493}, c: 1, iid: "", tid: "bluebGrt"}], id: "fd"}, med: {it: [], id: "med"},
                res: {it: [{c: 4, iid: "", tid: "stn"}, {c: 7, iid: "", tid: "wd"}, {c: 1, iid: "", tid: "wst"}],
                      id: "res"}, pic: {it: [], id: "pic"},
                cts: {it: [{atr: {bt: 1685947775}, c: 1, iid: "", tid: "bShrt1"}], id: "cts"},
                frt: {it: [], id: "frt"}}}}]"""
        # ["a.clths.wear", {clths: {clths: [{tpid: "bPnts1", clid: ""}, {tpid: "bShs1", clid: ""}]}}]
        ctp = "casual"
        wearing = await self.server.redis.smembers(f"uid:{client.uid}:{ctp}")
        for cloth in wearing:
            await self.server.inv[client.uid].change_wearing(cloth, False)
        clths = msg[2]["clths"]
        for cloth in clths:
            if cloth["clid"]:
                tmp = f"{cloth['tpid']}_{cloth['clid']}"
            else:
                tmp = cloth["tpid"]
            await self.server.inv[client.uid].change_wearing(tmp, True)
        inv = self.server.inv[client.uid].get()
        await client.send(["ntf.invch", {"inv": inv}])
        clths = await self.server.get_clothes(client.uid, type_=2)
        await client.send(["a.clths.wear", {"clths": clths}])
        await refresh_avatar(client, self.server)
    
    async def buy_clothes(self, command, clothes, client):
        items = await self.server.redis.smembers(f"uid:{client.uid}:items")
        if (await self.server.get_appearance(client.uid))["g"] == 1:
            gender = "boy"
        else:
            gender = "girl"
        gold = 0
        silver = 0
        rating = 0
        to_buy = []
        user_data = await self.server.get_user_data(client.uid)
        for item in clothes:
            cloth = item["tpid"]
            clid = item["clid"]
            if clid:
                name = f"{cloth}_{clid}"
            else:
                name = cloth
            if name in items or cloth in items:
                continue
            tmp = self.server.clothes[gender][cloth]
            gold += tmp["gold"]
            silver += tmp["silver"]
            rating += tmp["rating"]
            if clid:
                to_buy.append(name)
            else:
                to_buy.append(cloth)
        if not to_buy or user_data["gld"] < gold or user_data["slvr"] < silver:
            return
        pipe = self.server.redis.pipeline()
        pipe.set(f"uid:{client.uid}:gld", user_data["gld"] - gold)
        pipe.set(f"uid:{client.uid}:slvr", user_data["slvr"] - silver)
        await pipe.execute()
        for cloth in to_buy:
            await self.server.inv[client.uid].add_item(cloth, "cts")
            await self.server.inv[client.uid].change_wearing(cloth, True)
        user_data = await self.server.get_user_data(client.uid)
        inv = self.server.inv[client.uid].get()
        clths = await self.server.get_clothes(client.uid, type_=2)
        ccltn = await self.server.get_clothes(client.uid, type_=1)
        ccltn = ccltn["ccltns"]["casual"]
        await client.send([command, {"inv": inv,
                                     "clths": clths, "ccltn": ccltn,
                                     "crt": user_data["crt"]}])
        await update_resources(client, self.server)
    
    async def buy_clothes_suit(self, tpid, client):
        if (await self.server.get_appearance(client.uid))["g"] == 1:
            gender = "boy"
        else:
            gender = "girl"
        if tpid not in self.sets[gender]:
            logging.info(f"Set {tpid} not found")
            return
        gold = 0
        silver = 0
        rating = 0
        items = await self.server.redis.smembers(f"uid:{client.uid}:items")
        to_buy = []
        user_data = await self.server.get_user_data(client.uid)
        for cloth in self.sets[gender][tpid]:
            if ":" in cloth:
                cloth = cloth.replace(":", "_")
            if cloth in items:
                continue
            attrs = self.server.clothes[gender][cloth]
            gold += attrs["gold"]
            silver += attrs["silver"]
            rating += attrs["rating"]
            to_buy.append(cloth)
        if user_data["gld"] < gold or user_data["slvr"] < silver:
            return
        await self.server.redis.set(f"uid:{client.uid}:gld",
                                    user_data["gld"] - gold)
        await self.server.redis.set(f"uid:{client.uid}:slvr",
                                    user_data["slvr"] - silver)
        await self.server.redis.set(f"uid:{client.uid}:crt",
                                    user_data["crt"] + rating)
        for cloth in to_buy:
            await self.server.inv[client.uid].add_item(cloth, "cts")
            await self.server.inv[client.uid].change_wearing(cloth, True)
        inv = self.server.inv[client.uid].get()
        clths = await self.server.get_clothes(client.uid, type_=2)
        ccltn = await self.server.get_clothes(client.uid, type_=1)
        user_data = await self.server.get_user_data(client.uid)
        ccltn = ccltn["ccltns"]["casual"]
        await client.send(["a.clths.buy", {"inv": inv,
                                           "clths": clths, "ccltn": ccltn,
                                           "crt": user_data["crt"]}])
        await update_resources(client, self.server)
    
    async def update_appearance(self, apprnc, client):
        old = await self.server.get_appearance(client.uid)
        if old:
            nick = old["n"]
        else:
            nick = apprnc["n"]
        redis = self.server.redis
        await redis.delete(f"uid:{client.uid}:appearance")
        await redis.rpush(f"uid:{client.uid}:appearance", nick,
                          apprnc["nct"], apprnc["g"], apprnc["sc"],
                          apprnc["ht"], apprnc["hc"], apprnc["brt"],
                          apprnc["brc"], apprnc["et"], apprnc["ec"],
                          apprnc["fft"], apprnc["fat"], apprnc["fac"],
                          apprnc["ss"], apprnc["ssc"], apprnc["mt"],
                          apprnc["mc"], apprnc["sh"], apprnc["shc"],
                          apprnc["rg"], apprnc["rc"], apprnc["pt"],
                          apprnc["pc"], apprnc["bt"], apprnc["bc"])
    
    async def update_crt(self, uid):
        redis = self.server.redis
        clothes = []
        for tmp in await redis.smembers(f"uid:{uid}:items"):
            if await redis.lindex(f"uid:{uid}:items:{tmp}", 0) == "cls":
                if "_" in clothes:
                    clothes.append(tmp.split("_")[0])
                else:
                    clothes.append(tmp)
        appearance = await self.server.get_appearance(uid)
        if not appearance:
            return 0
        gender = "boy" if appearance["g"] == 1 else "girl"
        crt = 0
        for cloth in clothes:
            for _category in self.clothes_list[gender]:
                for item in self.clothes_list[gender][_category]:
                    if item == cloth:
                        item = self.clothes_list[gender][_category][cloth]
                        crt += item["rating"]
                        break
        await self.server.redis.set(f"uid:{uid}:crt", crt)
        return crt
    
    def get_category(self, cloth, gender):
        if "_" in cloth:
            cloth = cloth.split("_")[0]
        for category in self.clothes_list:
            for item in self.clothes_list[category]:
                if item == cloth:
                    return category
        return None
