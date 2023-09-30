import xml.etree.ElementTree as ET


class Parser():
    def __init__(self):
        self.apprnc_map = ["sc", "et", "brt", "mt", "ht", "bt", "sh", "rg",
                           "ss", "pt", "fat", "fft"]
    
    def parse_build(self):
        builds = {}
        root = ET.parse(f"config_all_ru/inventory/buildings.xml").getroot()
        for build in root.findall(".//item"):
            if "id" not in build.attrib:
                continue
            builds[build.attrib['id']] = {}
            maxBuy = 30
            canRemove = False
            gold = 0
            silver = 0
            if "buyCount" in build.attrib:
                maxBuy = int(build.attrib['buyCount'])
            if "canRemove" in build.attrib:
                canRemove = bool(build.attrib['canRemove'])
            if "gold" in build.attrib:
                gold = int(build.attrib['gold'])
            if "silver" in build.attrib:
                silver = int(build.attrib['silver'])
            if "minLevel" in build.attrib:
                minLevel = int(build.attrib['minLevel'])
            builds[build.attrib['id']]["maxBuy"] = maxBuy
            builds[build.attrib['id']]["canRemove"] = canRemove
            builds[build.attrib['id']]["silver"] = silver
            builds[build.attrib['id']]["gold"] = gold
            builds[build.attrib['id']]["min_level"] = minLevel
            builds[build.attrib['id']]["lvl"] = {}
            for lvl in build.findall(".//level"):
                builds[build.attrib['id']]["lvl"][lvl.attrib["id"]] = {}
                for phase in lvl.findall(".//phase"):
                    try:
                        builds[build.attrib['id']]["lvl"][lvl.attrib["id"]][phase.attrib["level"]] = {}
                        for cost in phase.findall(".//cost"):
                            builds[build.attrib['id']]["lvl"][lvl.attrib["id"]][phase.attrib["level"]]["gold"] = int(
                                cost.attrib["gold"])
                            builds[build.attrib['id']]["lvl"][lvl.attrib["id"]][phase.attrib["level"]]["silver"] = int(
                                cost.attrib["silver"])
                            builds[build.attrib['id']]["lvl"][lvl.attrib["id"]][phase.attrib["level"]]["items"] = []
                            for needitem in cost:
                                builds[build.attrib['id']]["lvl"][lvl.attrib["id"]][phase.attrib["level"]]["items"].append(
                                    {"id": needitem.attrib["typeId"], "count": int(needitem.attrib["count"])}
                                )
                    except Exception:
                        continue
        
        return builds
    
    def parse_weeds(self):
        weeds = {}
        root = ET.parse(f"config_all_ru/inventory/weeds.xml").getroot()
        for cat in root.findall(".//category"):
            weeds[cat.attrib["id"]] = {"regenerateSpeed": int(cat.attrib["regenerateSpeed"]), "obj": {}}
            for item in cat.findall(".//item"):
                if 'interactCount' in item.attrib:
                    weeds[cat.attrib["id"]]["obj"][item.attrib["id"]] = {"ic": int(item.attrib["interactCount"])}
                else:
                    weeds[cat.attrib["id"]]["obj"][item.attrib["id"]] = {"ic": 10}
        return weeds
    
    def parse_resources(self):
        res = {}
        root = ET.parse(f"config_all_ru/inventory/resources.xml").getroot()
        for item in root.findall(".//item"):
            res[item.attrib["id"]] = {"silver": 0, "gold": 0, "saleSilver": 0}
            if "silver" in item.attrib:
                res[item.attrib["id"]]["silver"] = int(item.attrib["silver"])
            if "gold" in item.attrib:
                res[item.attrib["id"]]["gold"] = int(item.attrib["gold"])
            if "saleSilver" in item.attrib:
                res[item.attrib["id"]]["saleSilver"] = int(item.attrib["saleSilver"])
        return res
    
    def parse_foods(self):
        res = {}
        root = ET.parse(f"config_all_ru/inventory/food.xml").getroot()
        for item in root.findall(".//item"):
            res[item.attrib["id"]] = {}
            for mod in item.findall(".//modifier"):
                res[item.attrib["id"]][mod.attrib["name"]] = int(mod.attrib["effect"])
        return res
    
    def parse_med(self):
        res = {}
        root = ET.parse(f"config_all_ru/inventory/medicine.xml").getroot()
        for item in root.findall(".//item"):
            res[item.attrib["id"]] = {}
            for mod in item.findall(".//modifier"):
                res[item.attrib["id"]][mod.attrib["name"]] = int(mod.attrib["effect"])
        return res
    
    def parse_plants(self):
        plants = {}
        root = ET.parse(f"config_all_ru/inventory/seeds.xml").getroot()
        for item in root.findall(".//item"):
            plants[item.attrib["id"]] = {"silver": int(item.attrib['silver']), "gold": int(item.attrib['gold']),
                                         "ripen": {}}
            for ripen in item.findall(".//ripen"):
                plants[item.attrib["id"]]["ripen"]["typeId"] = ripen.attrib["typeId"]
                plants[item.attrib["id"]]["ripen"]["time"] = int(ripen.attrib["time"])
                plants[item.attrib["id"]]["ripen"]["seasons"] = int(ripen.attrib["seasons"])
        return plants
    
    def parse_conflicts(self):
        doc = ET.parse("config_all_ru/inventory/extend/clothesRules.xml")
        root = doc.getroot()
        conflicts = []
        for rule in root.findall(".//rule"):
            conflicts.append([rule.attrib["category1"],
                              rule.attrib["category2"]])
        return conflicts
    
    def parse_category_clothes(self):
        clothes = {"boy": {}, "girl": {}}
        root = ET.parse(f"config_all_ru/inventory/clothes.xml").getroot()
        for category in root.findall(".//category[@logCategory2]"):
            name = category.attrib["logCategory2"][1:]
            clothes[name] = self.parse_clothes_category_item(category)
        return clothes
    
    def parse_clothes_category_item(self, category):
        tmp = {}
        for item in category:
            name = item.attrib["id"]
            tmp[name] = None
        return tmp
    
    def parse_clothes(self):
        cloth = {"boy": {}, "girl": {}}
        root = ET.parse(f"config_all_ru/inventory/clothes.xml").getroot()
        for cat in root.findall(".//category"):
            if "gender" not in cat.attrib:
                continue
            gender = cat.attrib['gender']
            for item in cat.findall(".//item"):
                try:
                    cloth[gender][item.attrib["id"]] = {"rating": int(item.attrib["rating"]),
                                                        "gold": int(item.attrib["gold"]),
                                                        "silver": int(item.attrib["silver"])}
                except:
                    continue
                    # it's clothes can't buy
        return cloth
    
    def parse_appearance(self):
        doc = ET.parse("config_all_ru/avatarAppearance/appearance.xml")
        root = doc.getroot()
        apprnc = {"boy": {}, "girl": {}}
        for gender in ["boy", "girl"]:
            el = root.find(gender)
            for category in el.findall("category"):
                id_ = int(category.attrib["id"])
                map_ = self.apprnc_map[id_]
                apprnc[gender][map_] = {}
                for item in category.findall("item"):
                    try:
                        kind = int(item.attrib["kind"])
                    except ValueError:
                        continue
                    apprnc[gender][map_][kind] = {}
                    for attr in ["silver", "gold", "brush", "visagistLevel"]:
                        if attr in item.attrib:
                            value = int(item.attrib[attr])
                            apprnc[gender][map_][kind][attr] = value
                    for attr in ["salonOnly"]:
                        if attr in item.attrib:
                            apprnc[gender][map_][kind][attr] = True
        return apprnc
    
    def parse_relations(self):
        doc = ET.parse("config_all_ru/modules/relations.xml")
        root = doc.getroot()
        statuses = {}
        tmp = root.find(".//statuses")
        for status in tmp.findall("status"):
            id_ = int(status.attrib["id"])
            statuses[id_] = {"transition": [], "progress": {}}
            for progress in status.findall("progress"):
                value = int(progress.attrib["value"])
                tmp_status = int(progress.attrib["status"])
                statuses[id_]["progress"][value] = tmp_status
            for trans in status.findall("statusForTransition"):
                tmp_id = int(trans.attrib["id"])
                statuses[id_]["transition"].append(tmp_id)
        return statuses
    
    def parse_clothes_sets(self):
        doc = ET.parse("config_all_ru/inventory/extend/clothesSets.xml")
        root = doc.getroot()
        sets = {"boy": {}, "girl": {}}
        for clset in root.findall(".//clothesSet"):
            sets[clset.attrib["gender"]][clset.attrib["id"]] = []
            for item in clset.findall(".//item"):
                sets[clset.attrib["gender"]][clset.attrib["id"]].append(item.attrib["itemId"])
        return sets
    
    def parse_relation_progresses(self):
        doc = ET.parse("config_all_ru/modules/relations.xml")
        root = doc.getroot()
        progresses = {}
        tmp = root.find(".//progresses")
        for progress in tmp.findall("progress"):
            value = int(progress.attrib["value"])
            progresses[progress.attrib["reason"]] = value
        return progresses
    
    def parse_daily_gift(self):
        doc = ET.parse("config_all_ru/modules/dailyGift.xml")
        root = doc.getroot()
        gifts = {}
        i = 1
        for itemDay in root.findall(".//gift"):
            gifts[i] = {attr: itemDay.attrib[attr] for attr in itemDay.attrib}
            i += 1
        return gifts
    
    def parse_game_items(self):
        doc = ET.parse("config_all_ru/inventory/game.xml")
        root = doc.getroot()
        game = {}
        for item in root.findall(".//item"):
            game[item.attrib["id"]] = {attr: item.attrib[attr] for attr in item.attrib}
        return game
