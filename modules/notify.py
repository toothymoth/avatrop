
async def update_resources(client, server):
    user_data = await server.get_user_data(client.uid)
    await client.send(["ntf.resch", {'res': {'rb': 0, 'enrg': user_data['enrg'], 'gld': user_data['gld'], 'vmd': 0,
                                             'slvr': user_data['slvr'], 'vtlt': 0, 'emd': 0, 'bns': 0}}])
    

