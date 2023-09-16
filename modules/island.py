
import time
import asyncio
from modules.location import gen_plr
from modules.location import Location
from inventory import Inventory
from modules.base_module import Module

class_name = "Island"


class Island(Module):
    prefix = "ild"
    
    def __init__(self, server):
        self.server = server
        self.kicked = {}
        self.orderItems = self.server.parser.parse_game_items()
        self.commands = {"gi": self.get_my_info, "gild": self.get_room, "obi": self.order}
    
    async def get_my_info(self, msg, client):
        if "lid" in msg[2]:
            if msg[2]['lid'] == "beach":
                loc = msg[2]['lid'] + "_" + msg[2]["gid"] + "_1"
                await client.send(["r.jn", {'plr': await gen_plr(client, self.server)}])
                await client.send([loc, client.uid])
                await client.send(["ild.gi", {"rid": loc}])
                return
        apprnc = await self.server.get_appearance(client.uid)
        if not apprnc:
            return await client.send(["ild.gi", {"has.avtr": False}])
        user_data = await self.server.get_user_data(client.uid)
        if client.uid not in self.server.inv:
            self.server.inv[client.uid] = Inventory(self.server, client.uid)
            await self.server.inv[client.uid]._get_inventory()
        inv = self.server.inv[client.uid].get()
        plr = await gen_plr(client, self.server)
        plr['res'] = {"slvr": user_data["slvr"], "enrg": user_data["enrg"],
                      "emd": user_data["emd"], "gld": user_data["gld"], "vtlt": 0,
                      "rb": 0, "vmd": 0}
        plr['inv'] = inv
        plr['qc'] = {'q': [{'ts': [{'pr': 0, 'ind': 0, 'tp': "ufrt"}], 'a': True, 'qid': "q1"}]}
        await client.send(["ild.gi", {"plr": plr, "tm": 1}])
        await self._perform_login(client)
        
    async def order(self, msg, client):
        ordims = self.orderItems
        item = msg[2]["tpid"]
        pind = int(msg[2]["pind"])
        if pind == 1:
            gold = int(ordims[item]["gold"])
            silver = 0
        else:
            silver = int(ordims[item]["silver"])
            gold = 0
        await client.send(msg[1:])
            
        #  [None, 'ild.obi', {'tpid': 'bmPnCl', 'pind': 1}]}
    
    async def get_room(self, msg, client):
        room = msg[2]['rid']
        if not room:
            room = f"farm_{client.uid}_ild"
        if client.room:
            await Location(self.server).leave_room(client)
        await Location(self.server).join_room(client, room)
        # await self.owner_at_house(client.uid, True)
        await client.send(["ild.gild", {"rid": client.room, "uid": msg[2]['uid']}])
    
    async def _perform_login(self, client):
        await self.server.modules["isin"].commands["shdgd"](client)
    
    async def _background(self):
        while True:
            for owner in self.kicked.copy():
                for uid in self.kicked[owner]:
                    if time.time() - self.kicked[owner][uid] >= 1800:
                        del self.kicked[owner][uid]
            await asyncio.sleep(60)
