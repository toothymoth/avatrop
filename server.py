import json
from importlib import import_module
import asyncio
import logging
from datetime import datetime
import time
import aioredis
from client import Client
from inventory import Inventory
from modules.location import Location
from xml_parser import Parser

modules: list = ["island", "avatar",
                 "relations", "social_request",
                 "billing", "component",
                 "passport", "player", "statistics", "shop", "confirm",
                 "chat_decor", "access_location", "location", "income", "inventory", "pet"]


class Server():
    def __init__(self):
        self.online = {}
        self.rooms = {}
        self.inv = {}
        self.parser = Parser()
        # self.conflicts = self.parser.parse_conflicts()
        # self.achievements = self.parser.parse_achievements()
        # self.trophies = self.parser.parse_trophies()
        # self.game_items = self.parser.parse_game_items()
        # self.appearance = self.parser.parse_appearance()
        self.clothes = self.parser.parse_clothes()
        self.plants = self.parser.parse_plants()
        self.build = self.parser.parse_build()
        self.conflicts = self.parser.parse_conflicts()
        self.modules = {}
        for item in modules:
            module = import_module(f"modules.{item}")
            class_ = getattr(module, module.class_name)
            self.modules[class_.prefix] = class_(self)
        self.kicked = []
    
    async def listen(self):
        self.redis = await aioredis.create_redis_pool("redis://localhost",
                                                      encoding="utf-8")
        loop = asyncio.get_event_loop()
        for prefix in self.modules:
            module = self.modules[prefix]
            if hasattr(module, "_background"):
                loop.create_task(module._background())
            if hasattr(module, "background_two"):
                loop.create_task(module.background_two())
        self.server = await asyncio.start_server(self.new_conn,
                                                 "0.0.0.0", 8123)
        loop.create_task(self._background())
        logging.info("Сервер успешно запущен!")
    
    async def stop(self):
        logging.info("Выключение...")
        for uid in self.online.copy():
            try:
                await self.online[uid].send([6, "Restart", {}], type_=2)
            except Exception:
                continue
        self.server.close()
        await self.server.wait_closed()
    
    async def new_conn(self, reader, writer):
        loop = asyncio.get_event_loop()
        loop.create_task(Client(self).handle(reader, writer))
    
    async def process_data(self, data, client):
        print(data)
        if not client.uid:
            if data["type"] != 1:
                return client.writer.close()
            return await self.auth(data["msg"], client)
        if data["type"] == 2:
            return client.writer.close()
        elif data["type"] == 17:
            if client.room:
                await Location(self).leave_room(client)
            await client.send([data["msg"][0], client.uid], type_=17)
        elif data["type"] == 34:
            if data["msg"][1] == "clerr":
                return
            if client.uid in self.msgmeter:
                self.msgmeter[client.uid] += 1
                if self.msgmeter[client.uid] > 110:
                    # if client.uid in self.kicked:
                    # return client.writer.close()
                    # self.kicked.append(client.uid)
                    logging.debug(f"Кик {client.uid} за превышение лимитов")
                    await client.send(["cp.ms.rsm", {"txt": "Вы были кикнуты "
                                                            "за превышение "
                                                            "лимитов"}])
                    # await client.send([5, "Limits kick", {}], type_=2)
                    return client.writer.close()
            else:
                self.msgmeter[client.uid] = 1
            client.last_msg = time.time()
            prefix = data["msg"][1].split(".")[0]
            if prefix not in self.modules:
                return logging.warning(f"Command {data['msg'][1]} not found")
            await self.modules[prefix].on_message(data["msg"], client)
            # asyncio.create_task(self.modules[prefix].on_message(data["msg"],
            #                                                    client))
    
    async def get_exp(self, level):
        expSum = 0
        for i in range(0, level):
            expSum += i * 50
        return expSum
    
    async def get_lvl(self, exp):
        expSum = 0
        lvl = 0
        while expSum <= exp:
            lvl += 1
            expSum += lvl * 50
        return lvl
    
    async def auto_ban(self, uid):
        await self.redis.set(f"uid:{uid}:banned", 0)
        await self.redis.set(f"uid:{uid}:ban_time", int(time.time()))
        await self.redis.set(f"uid:{uid}:ban_end", 0)
        await self.redis.set(f"uid:{uid}:ban_reason", "Чит!")
        message = f"{uid} получил автобан\nПричина: читы"
        await self.modules["cp"].send_tg(message)
    
    async def auth(self, msg, client):
        uid = msg[1]
        method = msg[0]
        banned = await self.redis.get(f"uid:{uid}:banned")
        if banned:
            ban_time = int(await self.redis.get(f"uid:{uid}:ban_time"))
            ban_end = int(await self.redis.get(f"uid:{uid}:ban_end"))
            reason = await self.redis.get(f"uid:{uid}:ban_reason")
            if not reason:
                reason = ""
            category = await self.redis.get(f"uid:{uid}:ban_category")
            if category:
                category = int(category)
            else:
                category = 4
            if ban_end == 0:
                time_left = 0
            else:
                time_left = ban_end - int(time.time() * 1000)
            if time_left < 0 and ban_end != 0:
                await self.redis.delete(f"uid:{uid}:banned")
                await self.redis.delete(f"uid:{uid}:ban_time")
                await self.redis.delete(f"uid:{uid}:ban_end")
                await self.redis.delete(f"uid:{uid}:ban_reason")
            else:
                await client.send([10, "User is banned",
                                   {"duration": 999999, "banTime": ban_time,
                                    "notes": reason, "reviewerId": banned,
                                    "reasonId": category, "unbanType": "none",
                                    "leftTime": time_left, "id": None,
                                    "reviewState": 1, "userId": uid,
                                    "moderatorId": banned}], type_=2)
                client.writer.close()
                return
        if uid in self.online:
            try:
                await self.online[uid].send([6, {}], type_=3)
                self.online[uid].writer.close()
            except OSError:
                pass
        if not await self.redis.get(f"uid:{uid}:exp"):
            await self.redis.set(f"uid:{uid}:slvr", 1000)
            await self.redis.set(f"uid:{uid}:gld", 100)
            await self.redis.set(f"uid:{uid}:level", 2)
            await self.redis.set(f"uid:{uid}:enrg", 100)
            await self.redis.set(f"uid:{uid}:exp", 493500)
            await self.redis.set(f"uid:{uid}:emd", 0)
            await self.redis.set(f"uid:{uid}:lvt", 0)
        client.uid = uid
        client.user_data["id"] = uid
        self.online[uid] = client
        await self.redis.set(f"uid:{uid}:lvt", int(time.time()))
        # await self.check_new_act(client, await self.redis.incrby(f"uid:{uid}:lvt", 0))
        await self.redis.set(f"uid:{uid}:ip", client.addr)
        if uid not in self.inv and method != "account":
            self.inv[uid] = Inventory(self, uid)
            await self.inv[uid]._get_inventory()
        await client.send([client.uid, "", True, False, False], type_=1)
        print(client.room)
        client.checksummed = True
        if method == "account":
            await client.send([7, {}], type_=3)
    
    async def check_new_act(self, client, lvt):
        now = datetime.now()
        old = datetime.fromtimestamp(lvt)
        give = False
        if now.day - old.day == 1:
            give = True
        else:
            delta = now - old
            if now.day != old.day:
                if delta.days <= 1:
                    give = True
                else:
                    await self.redis.delete(f"uid:{client.uid}:days")
        if give:
            strik = await self.redis.get(f"uid:{client.uid}:days")
            if not strik:
                strik = 1
            else:
                strik = int(strik)
                if strik >= 5:
                    if await self.redis.get(f"uid:{client.uid}:premium") and strik < 8:
                        strik += 1
                else:
                    strik += 1
            await self.redis.incrby(f"uid:{client.uid}:act", strik)
            await self.redis.set(f"uid:{client.uid}:days", strik)
    
    async def remove_premium(self, uid):
        await self.redis.delete(f"uid:{uid}:premium")
    
    async def _get_user_data(self, uid):
        pipe = self.redis.pipeline()
        level = await self.redis.get(f"uid:{uid}:level")
        pipe.get(f"uid:{uid}:slvr")
        pipe.get(f"uid:{uid}:enrg")
        pipe.get(f"uid:{uid}:gld")
        pipe.get(f"uid:{uid}:exp")
        pipe.get(f"uid:{uid}:emd")
        pipe.get(f"uid:{uid}:lvt")
        pipe.get(f"uid:{uid}:trid")
        pipe.get(f"uid:{uid}:crt")
        pipe.get(f"uid:{uid}:hrt")
        pipe.get(f"uid:{uid}:act")
        pipe.get(f"uid:{uid}:role")
        pipe.get(f"uid:{uid}:premium")
        result = await pipe.execute()
        if not result[0]:
            return None
        if result[5]:
            lvt = int(result[5])
        else:
            lvt = 0
        if result[7]:
            crt = int(result[7])
        else:
            crt = await self.modules["a"].update_crt(uid)
        if result[8]:
            hrt = int(result[8])
        else:
            hrt = await self.modules["frn"].update_hrt(uid)
        if result[9]:
            act = int(result[9])
        else:
            act = 0
        if result[10]:
            role = int(result[10])
        else:
            role = 0
        premium = False
        if result[11]:
            prem_time = int(result[11])
            if prem_time == 0 or prem_time - time.time() > 0:
                premium = True
        else:
            prem_time = 0
        return {"uid": uid, "slvr": int(result[0]), "enrg": int(result[1]),
                "gld": int(result[2]), "exp": int(result[3]),
                "emd": int(result[4]), "lvt": lvt, "crt": crt, "act": act,
                "hrt": hrt, "trid": result[6], "role": role,
                "premium": premium, "prem_time": prem_time}
    
    async def get_user_data(self, uid, cat=None):
        if cat:
            return await self.redis.incrby(f"uid:{uid}:{cat}", 0)
        data = {}
        for at in ["slvr", "enrg", "gld", "exp", "emd", "lvt", "trid", "crt",
                   "hrt", "act", "role", "level"]:
            if at == "trid":
                data["trid"] = await self.redis.get(f"uid:{uid}:trid")
            else:
                data[at] = await self.redis.incrby(f"uid:{uid}:{at}", 0)
        premium = False
        prem_time = 0
        if await self.redis.get(f"uid:{uid}:premium"):
            prem_time = int(await self.redis.get(f"uid:{uid}:premium"))
            if prem_time == 0 or prem_time - time.time() > 0:
                premium = True
        data.update({"premium": premium, "prem_time": prem_time});
        return data
    
    async def get_appearance(self, uid):
        apprnc = await self.redis.lrange(f"uid:{uid}:appearance", 0, -1)
        if not apprnc:
            return False
        return {"n": apprnc[0], "nct": int(apprnc[1]), "g": int(apprnc[2]),
                "sc": int(apprnc[3]), "ht": int(apprnc[4]),
                "hc": int(apprnc[5]), "brt": int(apprnc[6]),
                "brc": int(apprnc[7]), "et": int(apprnc[8]),
                "ec": int(apprnc[9]), "fft": int(apprnc[10]),
                "fat": int(apprnc[11]), "fac": int(apprnc[12]),
                "ss": int(apprnc[13]), "ssc": int(apprnc[14]),
                "mt": int(apprnc[15]), "mc": int(apprnc[16]),
                "sh": int(apprnc[17]), "shc": int(apprnc[18]),
                "rg": int(apprnc[19]), "rc": int(apprnc[20]),
                "pt": int(apprnc[21]), "pc": int(apprnc[22]),
                "bt": int(apprnc[23]), "bc": int(apprnc[24])}
    
    async def get_clothes(self, uid, type_):
        clothes = []
        cur_ctp = await self.redis.get(f"uid:{uid}:wearing")
        for item in await self.redis.smembers(f"uid:{uid}:{cur_ctp}"):
            if "_" in item:
                id_, clid = item.split("_")
                clothes.append({"id": id_, "clid": clid})
            else:
                clothes.append({"id": item, "clid": ""})
        if type_ == 1:
            ctps = ["casual", "club", "official", "swimwear", "underdress"]
            clths = {"cc": cur_ctp, "ccltns": {}}
            clths["ccltns"][cur_ctp] = {"cct": [], "cn": "", "ctp": cur_ctp}
            for item in clothes:
                if item["clid"]:
                    clths["ccltns"][cur_ctp]["cct"].append(f"{item['id']}:"
                                                           f"{item['clid']}")
                else:
                    clths["ccltns"][cur_ctp]["cct"].append(item["id"])
            ctps.remove(cur_ctp)
            for ctp in ctps:
                clths["ccltns"][ctp] = {"cct": [], "cn": "", "ctp": ctp}
                clothes = []
                for item in await self.redis.smembers(f"uid:{uid}:{ctp}"):
                    if "_" in item:
                        id_, clid = item.split("_")
                        clothes.append({"id": id_, "clid": clid})
                    else:
                        clothes.append({"id": item, "clid": ""})
                for item in clothes:
                    if item["clid"]:
                        clths["ccltns"][ctp]["cct"].append(f"{item['id']}:"
                                                           f"{item['clid']}")
                    else:
                        clths["ccltns"][ctp]["cct"].append(item["id"])
        elif type_ == 2:
            clths = {"clths": []}
            for item in clothes:
                clths["clths"].append({"tpid": item["id"],
                                       "clid": item["clid"]})
        elif type_ == 3:
            clths = {"cct": [], "cn": "", "ctp": cur_ctp}
            for item in clothes:
                if item["clid"]:
                    clths["cct"].append(f"{item['id']}:{item['clid']}")
                else:
                    clths["cct"].append(item["id"])
        return clths
    
    async def get_island(self, uid):
        # "ir": 2,
        #       "x": 64,
        #       "y": 29,
        #       "tid": "wb5",
        #       "d": 5,
        #       "id": 583
        # {sut: 0, ast: 0, n: "Лентяй", stp: null, exp: 0, aid: null, id: 3439172, oid: "20111672", psy: 49, rt: 0, tid: "petCGgr", psx: 25, c: {lut: 1649655878, l: [{n: "st", v: 0}, {n: "cf", v: 100}, {n: "hp", v: 0}, {n: "hl", v: 0}, {n: "hg", v: 0}], ui: []}
        r = self.redis
        map = {}
        catsMap = ["ws", "pts", "t", "b", "dc", "np"]
        map["m"] = "isl_1"
        map["l"] = 10
        map["r"] = await self.getPlants(uid, "ridge")
        for cat in catsMap:
            map[cat] = []
            items = await r.lrange(f"uid:{uid}:islandMap:{cat}", 0, -1)
            args = []
            if cat == "ws":
                args = ["ir", "x", "y", "tid", "d", "id"]
            # Не доработаны питомцы
            elif cat == "pts":
                petsModel = f"uid:{uid}:pets"
                pets = await r.lrange(petsModel, 0, -1)
                for pet in pets:
                    map[cat].append(await self.modules["pet"].commands["gtpt"](self.online[uid], pet))
                continue
            elif cat == "b":
                """"x": 15,
                  "sid": "default",
                  "y": 47,
                  "l": 0,
                  "tid": "hs",
                  "pl": 0,
                  "d": 3,
                  "id": 484"""
                # builds
                args = ["x", "sid", "y", "l", "tid", "pl", "d", "id"]
            elif cat == "np":
                """"stp": 0,
                "x": 15,
                "y": 39,
                "npc": "npc1",
                "tid": null,
                "d": 5,
                "id": 1"""
                args = ["stp", "x", "y", "npc", "tid", "d", "id"]
            elif cat == "dc":
                """"x": 15,
                  "sid": "default",
                  "y": 47,
                  "l": 0,
                  "tid": "hs",
                  "pl": 0,
                  "d": 3,
                  "id": 484"""
                # builds
                args = ["x", "sid", "y",  "tid", "d", "id"]
            if not items:
                continue
            for item in items:
                argsItem = {}
                if cat == "b":
                    if await r.get(f"uid:{uid}:islandMap:{cat}:{item}:tid") == "phs":
                        housePet = await self.getPetInHouse(self.online[uid], item)
                        for hsPetArg in housePet:
                            argsItem[hsPetArg] = housePet[hsPetArg]
                for arg in args:
                    value = await r.get(f"uid:{uid}:islandMap:{cat}:{item}:{arg}")
                    if value.isdigit():
                        value = int(value)
                    elif value == "None":
                        value = None
                    argsItem[arg] = value
                map[cat].append(argsItem)
        return map
    
    async def getPetInHouse(self, client, house):
        r = self.redis
        uid = client.uid
        petsModel = f"uid:{uid}:pets"
        pets = await r.lrange(petsModel, 0, -1)
        if not pets:
            return {}
        for pet in pets:
            petModel = f"uid:{uid}:pet:{pet}:"
            if await r.get(petModel+"hid") == house:
                return {"ptid": await r.get(petModel+"tid"), "pn": await r.get(petModel+"nm"), "pid": pet}
    
    async def getArgsItemMapWS(self, client, itemId):
        r = self.redis
        uid = client.uid
        cat = "ws"
        args = ["ir", "x", "y", "tid", "d", "id"]
        argsItem = {}
        items = await r.lrange(f"uid:{uid}:islandMap:{cat}", 0, -1)
        if str(itemId) not in items:
            return {}
        for arg in args:
            value = await r.get(f"uid:{uid}:islandMap:{cat}:{itemId}:{arg}")
            if value.isdigit():
                value = int(value)
            elif value == "None":
                value = None
            argsItem[arg] = value
        return argsItem
    
    async def delItemMap(self, client, itemId, isPlant=False):
        r = self.redis
        uid = client.uid
        if not isPlant:
            cat = "ws"
            args = ["ir", "x", "y", "tid", "d", "id"]
            await r.lrem(f"uid:{uid}:islandMap:{cat}", 1, str(itemId))
            for arg in args:
                await r.delete(f"uid:{uid}:islandMap:{cat}:{itemId}:{arg}")
            return
        args = ["x", "y", "d", "ost", "gft", "stid", "tid", "gst", "gft"]
        await r.lrem(f"uid:{uid}:plants", 1, itemId)
        for arg in args:
            await r.delete(f"uid:{uid}:plants:{itemId}:{arg}")
    
    async def getPlants(self, uid, type_):
        r = self.redis
        plants = []
        Idplants = await r.lrange(f"uid:{uid}:plants", 0, -1)
        if not Idplants:
            return []
        for plantId in Idplants:
            if type_ == "ridge" and await r.get(f"uid:{uid}:plants:{plantId}:tid") != "ridge":
                continue
            elif type_ == "tree" and await r.get(f"uid:{uid}:plants:{plantId}:tid") == "ridge":
                continue
            args = {}
            for arg in ["x", "y", "d", "ost", "gft", "stid", "tid", "gst", "gft"]:
                value = await r.get(f"uid:{uid}:plants:{plantId}:{arg}")
                if value:
                    if value.isdigit():
                        value = int(value)
                if value == "None":
                    value = None
                args[arg] = value
            args["id"] = int(plantId)
            plants.append(args)
        return plants
    
    async def getPlant(self, client, type_, plid):
        for plant in await self.getPlants(client.uid, type_):
            if str(plant["id"]) == str(plid):
                return plant
    
    async def getLastNumObjectMap(self, client):
        r = self.redis
        uid = client.uid
        cat = "ws"
        maxId = 0
        objs = await r.lrange(f"uid:{uid}:islandMap:{cat}", 0, -1)
        for obj in objs:
            itemId = int(await r.get(f"uid:{uid}:islandMap:{cat}:{obj}:id"))
            if itemId > maxId:
                maxId = itemId
        return maxId
    
    async def newPlantMap(self, client, x, y, stid, d=5, tid="ridge"):
        # set new plant for map
        r = self.redis
        uid = client.uid
        cat = "ws"
        now = int(time.time())
        plantId = str(await self.getLastNumObjectMap(client) + 1 + await r.llen(f"uid:{uid}:plants"))  # get new id plant on map
        await r.rpush(f"uid:{uid}:plants", plantId)
        #  attrs for plant on map
        #  {x: 23, gft: 1685949107, ost: 1, tid: "ridge", stid: "bilbSd", gst: 1685947907, y: 49, d: 5, id: 574}
        await r.set(f"uid:{uid}:plants:{plantId}:x", x)
        await r.set(f"uid:{uid}:plants:{plantId}:y", y)
        await r.set(f"uid:{uid}:plants:{plantId}:d", d)
        await r.set(f"uid:{uid}:plants:{plantId}:tid", tid)
        await r.set(f"uid:{uid}:plants:{plantId}:stid", stid)
        await r.set(f"uid:{uid}:plants:{plantId}:gft", now + (self.plants[stid]["ripen"]["time"]*60))
        await r.set(f"uid:{uid}:plants:{plantId}:gst", now)
        await r.set(f"uid:{uid}:plants:{plantId}:ost", self.plants[stid]["ripen"]["seasons"])
        
    async def getFreeIdPlace(self, client) -> int:
        freeId = 1
        r = self.redis
        iids = []
        for cat in ["ws", "pts", "t", "b", "dc", "np"]:
            iids += await r.lrange(f"uid:{client.uid}:islandMap:{cat}", 0, -1)
        while freeId in list(map(int, iids)):
            freeId += 1
        return freeId

    async def addBuild(self, client, x, y, type_, catMap="b"):
        r = self.redis
        uid = client.uid
        attrs = ["x", "sid", "y", "l", "tid", "pl", "d", "id"]
        updMap = {}
        newId = await self.getFreeIdPlace(client)
        await r.rpush(f"uid:{uid}:islandMap:{catMap}", newId)
        for arg in attrs:
            if arg == "x":
                key = x
            elif arg == "y":
                key = y
            elif arg == "sid":
                key = "default"
            elif arg == "l":
                key = 0
            elif arg == "tid":
                key = type_
            elif arg == "pl":
                key = 0
            elif arg == "d":
                key = 3
            elif arg == "id":
                key = newId
            else:
                print(f"{arg} don't have need key")
            updMap[arg] = key
            await r.set(f"uid:{uid}:islandMap:{catMap}:{newId}:{arg}", key)
        commandUpdateMap = ["r.b.bobj",
                            {'uid': client.uid, 'fobj': updMap}]
        
        #await client.send(commandUpdateMap)
        await self.send_everybody_room(client.room, commandUpdateMap)
        
    async def send_everybody_room(self, room, msg):
        online = self.online
        room = self.rooms[room]
        for uid in room:
            try:
                tmp = online[uid]
            except KeyError:
                room.remove(uid)
                continue
            await tmp.send(msg)
        
    async def getArgsItemMapSmart(self, client, itemId, cat="b"):
        r = self.redis
        uid = client.uid
        if cat == "dc":
            args = ["x", "sid", "y", "tid", "d", "id"]
        else:
            with open("modules/default_map.json", "r") as f:
                defMap = json.load(f)
            try:
                args = defMap[cat][0].keys()
            except Exception as ex:
                print(ex)
                return {}
        argsItem = {}
        items = await r.lrange(f"uid:{uid}:islandMap:{cat}", 0, -1)
        if str(itemId) not in items:
            return {}
        for arg in args:
            value = await r.get(f"uid:{uid}:islandMap:{cat}:{itemId}:{arg}")
            if value.isdigit():
                value = int(value)
            elif value == "None":
                value = None
            argsItem[arg] = value
        return argsItem
        
    async def upgradeBuild(self, client, bid):
        r = self.redis
        uid = client.uid
        attr = "pl"
        catMap = "b"
        _phases = self.parser.parse_build()
        phases = len(_phases[await r.get(f"uid:{uid}:islandMap:{catMap}:{bid}:tid")]["lvl"][
            await r.get(f"uid:{uid}:islandMap:{catMap}:{bid}:l")])
        if await r.incrby(f"uid:{uid}:islandMap:{catMap}:{bid}:{attr}", 1) == phases:
            await r.incrby(f"uid:{uid}:islandMap:{catMap}:{bid}:l", 1)
        commandUpdateMap = ["r.b.upgbng",
                            {'uid': client.uid, 'fbng': await self.getArgsItemMapSmart(client, bid, "b")}]
        await client.send(commandUpdateMap)
    
    async def _background(self):
        autoKicked: bool = False
        while True:
            logging.info(f"Online: {len(self.online)}")
            logging.info(f"Rooms: {self.rooms}")
            self.msgmeter = {}
            self.kicked = []
            for uid in self.inv.copy():
                inv = self.inv[uid]
                if uid not in self.online and time.time() - inv.expire > 0:
                    del self.inv[uid]
            for uid in self.online.copy():
                if uid not in self.inv:
                    self.inv[uid] = Inventory(self, uid)
                    await self.inv[uid]._get_inventory()
            for uid in self.online.copy():
                nowTime: float = time.time()
                if uid not in self.online:
                    continue
                if await self.redis.get(f"uid:{uid}:premium"):
                    prem_time = float(int(await self.redis.get(f"uid:{uid}:premium")))
                    if prem_time != 0 and \
                            nowTime - prem_time > 0:
                        await self.remove_premium(uid)
                if autoKicked:
                    if nowTime - self.online[uid].last_msg > 420:
                        client = self.online[uid]
                        # logging.debug(f"Кик {client.uid} за афк")
                        await client.send(["cp.ms.rsm", {"txt": "Вы были кикнуты "
                                                                "за афк"}])
                        await client.send([3, {}], type_=3)
                        client.writer.close()
            await asyncio.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)-8s [%(asctime)s]  %(message)s",
                        datefmt="%H:%M:%S", level=logging.DEBUG)
    logging.getLogger("websockets").setLevel(logging.INFO)
    server = Server()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.listen())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(server.stop())
    loop.close()
