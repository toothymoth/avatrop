from modules.base_module import Module
from modules.location import refresh_avatar
import modules.notify as notify
import const

class_name = "ChatDecor"
            

class ChatDecor(Module):
    prefix = "chtdc"

    def __init__(self, server):
        self.server = server
        self.commands = {"schtm": self.save_chat_decor_model}

    async def save_chat_decor_model(self, msg, client):
        r = self.server.redis
        user_data = await self.server.get_user_data(client.uid)
        bubble = msg[2]["chtdc"]["bdc"]
        if not bubble:
            await r.delete(f"uid:{client.uid}:bubble")
        else:
            await r.set(f"uid:{client.uid}:bubble", bubble)
        text_color = msg[2]["chtdc"]["tcl"]
        if not text_color:
            await r.delete(f"uid:{client.uid}:tcl")
        else:
            await r.set(f"uid:{client.uid}:tcl", text_color)
        chat_bubble = msg[2]["chtdc"]["bt"]
        if not chat_bubble:
            await r.delete(f"uid:{client.uid}:chat_bubble")
        else:
            await r.set(f"uid:{client.uid}:chat_bubble", chat_bubble)
        bubble = await r.get(f"uid:{client.uid}:bubble")
        text_color = await r.get(f"uid:{client.uid}:tcl")
        chat_bubble = await r.get(f"uid:{client.uid}:chat_bubble")
        spks = ["bushStickerPack", "froggyStickerPack", "doveStickerPack",
                "jackStickerPack", "catStickerPack", "sharkStickerPack", "korgiStickerPack", "octopusStickerPack"]
        await client.send(["ntf.chtdcm", {"chtdc": {"bdc": bubble, "bt": chat_bubble,
                                                    "spks": spks,
                                                    "tcl": text_color}}])
        await client.send(["chtdc.schtm", {}])
        await refresh_avatar(client, self.server)