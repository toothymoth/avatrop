
from modules.base_module import Module
from client import Client
import common, json
from modules.notify import update_resources

with open("modules/default_map.json", "r") as f:
    default_map = json.load(f)

class_name = "Location"


class Location(Module):
    prefix = "r"
    
    def __init__(self, server):
        self.server = server
        self.commands = {"p": self.poop, "b": self.build}
        for cm in ["ust", "mv", "k", "sa", "sl", "bd", "lks", "hs",
                   "ks", "hg", "gf", "aks", "ra", "rinfo", "stact", "finact"]:
            self.commands[cm] = self.room
        self.actions = {"ks": "kiss", "hg": "hug", "gf": "giveFive",
                        "k": "kickAss", "sl": "slap", "lks": "longKiss",
                        "hs": "handShake", "aks": "airKiss"}
        
    async def build(self, msg, client):
        subcmd = msg[1].split(".")[-1]
        if subcmd == "bobj":
            await self.server.addBuild(client, msg[2]["x"], msg[2]["y"], msg[2]["tid"])
        elif subcmd == "bdobj":
            await self.server.addBuild(client, msg[2]["x"], msg[2]["y"], msg[2]["tid"], "dc")
        elif subcmd == "upgbng":
            await self.server.upgradeBuild(client, msg[2]["id"])
        elif subcmd == "mvobj":
            r = self.server.redis
            typeItem = None
            for tp in ["b", "dc", "t"]:
                if await self.server.getArgsItemMapSmart(client, msg[2]["id"], tp):
                    typeItem = tp
                    break
            if not typeItem:
                return
            await r.set(f"uid:{client.uid}:islandMap:{typeItem}:{msg[2]['id']}:x", msg[2]["x"])
            await r.set(f"uid:{client.uid}:islandMap:{typeItem}:{msg[2]['id']}:y", msg[2]["y"])
            msg.pop(0)
            msg[1]["fobj"] = await self.server.getArgsItemMapSmart(client, msg[1]['id'], typeItem)
            await client.send(msg)
        elif subcmd == "ei":
            msg[2]["l"] += 1
            await client.send(msg[1:])
        
    async def poop(self, msg, client):
        subcommand = msg[1].split(".")[-1]
        r = self.server.redis
        uid = client.uid
        # ["farm_20111672_ild", "r.p.si", {iid: 59}]
        if subcommand == "si":
            msg[2]["ir"] = await r.incrby(f"uid:{uid}:islandMap:ws:{msg[2]['iid']}:ir", -1)
            await client.send(msg[1:])
            if not msg[2]["ir"]:
                commandUpdateMap = ["r.w.uo",
                                    {'uid': uid, 'fobj': {}}]
            else:
                commandUpdateMap = ["r.w.uo", {'uid': uid, 'fobj': await self.server.getArgsItemMapWS(client, msg[2]['iid'])}]
            #await client.send(commandUpdateMap)
            await self.server.send_everybody_room(client.room, commandUpdateMap)
            tid = await self.server.getArgsItemMapWS(client, msg[2]['iid'])
            tid = tid["tid"][:-1]
            if tid == "ws":
                tid = "stn"
            elif tid == "wt":
                tid = "wd"
            else:
                tid = None
            await r.incrby(f"uid:{uid}:slvr", 3)
            await r.incrby(f"uid:{uid}:exp", 1)
            if tid:
                await self.server.inv[client.uid].add_item(tid, "res")
                inv = self.server.inv[client.uid].get()
                await client.send(["ntf.invch", {"inv": inv}])
            await client.send(["ntf.iich", {"ii": await get_island_info(client.uid, self.server)}])
            await update_resources(client, self.server)
            await client.send(["isl.drp", {'res': {'rb': 0, 'enrg': 0, 'gld': 0, 'vmd': 0, 'slvr': 3, 'vtlt': 0, 'emd': 0, 'bns': 0},
                                       'exp': 1, 'itms': [{'c': 1, 'iid': "", 'tid': tid}]}])
            if not msg[2]["ir"]:
                await self.server.delItemMap(client, msg[2]['iid'])
        #  ["farm_20111672_ild", "r.p.prs", {stid: "bilbSd", x: 23, y: 49, pind: 2}]
        elif subcommand == "prs":
            # new plant on map
            plantId = msg[2]["stid"]
            x = msg[2]["x"]
            y = msg[2]["y"]
            cat = "ws"
            num = await self.server.getLastNumObjectMap(client) + 1 + await r.llen(f"uid:{uid}:plants")
            if msg[2]["pind"] == 1:
                price = self.server.plants[plantId]["gold"]
                if not price or price < 0:
                    return
                await r.incrby(f"uid:{uid}:gld", -price)
            elif msg[2]["pind"] == 2:
                price = self.server.plants[plantId]["silver"]
                if not price or price < 0:
                    return
                await r.incrby(f"uid:{uid}:slvr", -price)
            await self.server.newPlantMap(client, x, y, plantId)
            infoPlant = await self.server.getPlants(client, "ridge")
            for inf in infoPlant:
                if int(inf["id"]) == num:
                    infoPlant = inf
            await client.send(["r.p.prs", {'frdg': infoPlant}])
            await client.send(["r.w.co", {'uid': uid, 'fobj': infoPlant}])
            await r.incrby(f"uid:{uid}:exp", 1)
            await client.send(["isl.drp", {'exp': 1}])
            await client.send(["ntf.iich", {"ii": await get_island_info(client.uid, self.server)}])
            await update_resources(client, self.server)
    
    async def room(self, msg, client):
        subcommand = msg[1].split(".")[1]
        r = self.server.redis
        if subcommand in ["ust", "mv", "k", "sa", "sl", "bd", "lks", "hs",
                          "ks", "hg", "gf", "aks"]:
            msg.pop(0)
            if msg[1]["uid"] != client.uid:
                return
            if "at" in msg[1]:
                if msg[1]["at"]:
                    if await r.decrby(f"uid:{client.uid}:enrg", 2) < 0:
                        await r.set(f"uid:{client.uid}:enrg", 0)
                        return
                    await update_resources(client, self.server)
                prefix = msg[0].split(".")[0]
            if subcommand == "ust":
                client.position = (msg[1]["x"], msg[1]["y"])
                client.direction = msg[1]["d"]
                if "at" in msg[1]:
                    client.action_tag = msg[1]["at"]
                else:
                    client.action_tag = ""
                client.state = msg[1]["st"]
            elif subcommand in self.actions:
                action = self.actions[subcommand]
                uid = msg[1]["tmid"]
                rl = self.server.modules["rl"]
                link = await rl.get_link(client.uid, uid)
                if link:
                    await rl.add_progress(action, link)
            online = self.server.online
            try:
                room = self.server.rooms[client.room].copy()
            except KeyError:
                room = [client.uid]
            for uid in room:
                try:
                    tmp = online[uid]
                except KeyError:
                    continue
                await tmp.send(msg)
        elif subcommand == "rinfo":
            rmmb = []
            try:
                room = self.server.rooms[msg[0]].copy()
            except KeyError:
                room = [client.uid]
            online = self.server.online
            for uid in room:
                try:
                    tmp = online[uid]
                except:
                    if uid == client.uid:
                        tmp = client
                    else:
                        continue
                rmmb.append(await gen_plr(tmp, self.server))
            if client.room:
                rr = client.room.split("_")[1]
            else:
                rr = client.uid
            map = await self.server.get_island(rr)
            await client.send(["r.rinfo", {"rmmb": rmmb, "frm": map,
                                           "l": 2, "r":
                                               await self.server.getPlants(client, "ridge")}])  # {"id": 486, "gft":
            # 0, "y": 49, "gst": 0, "x": 20,
            # "tid": "ridge", "d": 5, "stid": "strbSeed", "ost": 2}
        else:
            if subcommand == "ra" and not msg[2]:
                return await refresh_avatar(client, self.server)
            online = self.server.online
            room = self.server.rooms[client.room]
            for uid in room:
                try:
                    tmp = online[uid]
                except KeyError:
                    room.remove(uid)
                    continue
                await tmp.send(msg[1:])
    
    async def join_room(self, client, room):
        if room in self.server.rooms:
            self.server.rooms[room].append(client.uid)
        else:
            self.server.rooms[room] = [client.uid]
        client.room = room
        client.position = (-1.0, -1.0)
        client.action_tag = ""
        client.state = 0
        client.dimension = 4
        plr = await gen_plr(client, self.server)
        prefix = common.get_prefix(client.room)
        online = self.server.online
        new_room = self.server.rooms[room].copy()
        for uid in new_room:
            if uid not in online:
                continue
            tmp = online[uid]
            await tmp.send(["r.jn", {"plr": plr}])
            await tmp.send([client.room, client.uid], type_=16)
    
    async def leave_room(self, client):
        if not client.room:
            return
        if client.uid not in self.server.rooms[client.room]:
            return
        self.server.rooms[client.room].remove(client.uid)
        old_room = self.server.rooms[client.room].copy()
        if old_room:
            online = self.server.online
            for uid in old_room:
                try:
                    tmp = online[uid]
                except KeyError:
                    continue
                await tmp.send(["r.lv", {"uid": client.uid}])
                await tmp.send([client.room, client.uid], type_=17)
        else:
            del self.server.rooms[client.room]
        client.room = None


async def gen_plr(client, server):
    if isinstance(client, Client):
        uid = client.uid
    else:
        uid = client
    apprnc = await server.get_appearance(uid)
    if not apprnc:
        return None
    user_data = await server.get_user_data(uid)
    clths = await server.get_clothes(uid, type_=2)
    plr = {"uid": uid, "apprnc": apprnc, "clths": clths,
           "usrinf": {"rl": user_data["role"], "sid": uid}, "onl": True}
    if isinstance(client, Client):
        if await server.redis.get(f"uid:{uid}:loc_disabled"):
            shlc = False
        else:
            shlc = True
        plr["locinfo"] = {"st": client.state, "s": "127.0.0.1",
                          "at": client.action_tag, "d": client.dimension,
                          "x": -1, "y": -1, # client.position[0-1]
                          "shlc": shlc, "pl": "", "l": client.room}
    plr["ii"] = await get_island_info(uid, server)
    return plr


"""PARAM_EXP: String = "exp";
PARAM_TUTORIAL_STEP: String = "tst";
PARAM_PURCHASE_RECEPTS: String = "pcr";
PARAM_PETS_COUNT: String = "pcnt";
PARAM_CLOTHES_COUNT: String = "crt";
PARAM_EXPLORE_COUNT: String = "ert";
PARAM_GIFT_DAY_COUNT: String = "gdc";
PARAM_LAST_GIFT_TIME: String = "lgt";
PARAM_AVATAR_RATING: String = "avr";
PARAM_PET_RATING: String = "ptr";
PARAM_LAST_AVA_EXCHANGE_DAY: String = "aed";
PARAM_AVA_EXCHANGE_GOLD: String = "aeg";
PARAM_AVA_EXCHANGE_SILVER: String = "aes";
PARAM_SPENT_POINTS: String = "spp";"""


async def get_island_info(uid, server):
    user_data = await server.get_user_data(uid)
    tutorial = "finished"
    petsModel = f"uid:{uid}:pets"
    pets = await server.redis.lrange(petsModel, 0, -1)
    petsCount = len(pets)
    lastGiftTime = await server.redis.incrby(f"uid:{uid}:dailyTime", 0) - (24*60*60)
    petRating = await getPetRating(uid, server)
    giftDay = await server.redis.incrby(f"uid:{uid}:dailyDay", 0)
    ii = {'tst': tutorial,
          'aed': 0,
          'crt': user_data['crt'],
          'pcr': [],
          'aeg': 0,
          'pcnt': petsCount,
          'exp': user_data['exp'],
          'ert': 0,
          'lgt': lastGiftTime,
          'spp': -1,
          'aes': 0,
          'ptr': petRating,
          'avr': 0,
          'gdc': giftDay}
    return ii

async def getPetRating(uid, server):
    r = server.redis
    petsModel = f"uid:{uid}:pets"
    rating = 0
    pets = await r.lrange(petsModel, 0, -1)
    for pet in pets:
        petModel = f"uid:{uid}:pet:{pet}:"
        rating += int(await r.get(petModel+"rtg"))
    return rating


async def refresh_avatar(client, server):
    if not client.room:
        return
    plr = await gen_plr(client, server)
    online = server.online
    room = server.rooms[client.room].copy()
    for uid in room:
        try:
            tmp = online[uid]
        except KeyError:
            continue
        await tmp.send(["r.ra", {"plr": plr}])


async def get_exp(level):
    expSum = 0
    for i in range(0, int(level)):
        expSum += i * 50
    return expSum
