from flask import Flask, render_template, session, redirect, jsonify
from redis import Redis

app = Flask(__name__, static_folder='static')

xml = """<?xml version="1.0" ?>
<cross-domain-policy>
<allow-access-from domain="*" />
</cross-domain-policy>"""

HOST = "127.0.0.1"
PORT = 5000

redis = Redis(decode_responses=True)


def get_exp(level):
    expSum = 0
    for i in range(0, level):
        expSum += i * 50
    return expSum


@app.route('/')
def main():
    uid = 0
    token = None
    if "token" in session:
        token = session['token']
        uid = session['uid']
    return render_template("index.html", token=token, uid=uid)

@app.route('/logout')
def exit():
    del session['token']
    del session['uid']
    return redirect("/")


@app.route('/login', methods=["POST"])
def auth():
    uid = redis.incrby(f"uids", 1)
    if not redis.get(f"uid:{uid}:password"):
        # await bot_common.new_account()
        redis.set(f"uid:{uid}:slvr", 10000)
        redis.set(f"uid:{uid}:gld", 10000)
        redis.set(f"uid:{uid}:enrg", 150)
        redis.set(f"uid:{uid}:exp", 250)
        redis.set(f"uid:{uid}:emd", 0)
        redis.set(f"uid:{uid}:lvt", 0)
        redis.set(f"uid:{uid}:role", 0)
        redis.set(f"uid:{uid}:password", "example_token")
    session['uid'] = uid
    session['token'] = redis.get(f"uid:{uid}:password")
    return redirect("/")


@app.route("/prelogin")
def prelogin():
    return jsonify({"user": {"bannerNetworkId": None, "reg": 0,
                             "paymentGroup": "",
                             "preloginModuleIds": "", "id": 99,
                             "avatariaLevel": 999}})


@app.route("/auth_", methods=["POST"])
def auth_():
    return jsonify({"jsonrpc": "2.0", "id": 1,
                    "result": {"key": session['token'], "expireTime": 465753, "expireAt": 1676714400, "timeDelta": 2}})


@app.route("/crossdomain.xml")
def crossdomain():
    return render_template(xml), 201, {'Content-Type': 'application/json'}


@app.route("/method/<string:name>", methods=["POST"])
def method(name):
    if name == "friends.getAppUsers":
        return jsonify({"response": []})
    elif name == "friends.get":
        return jsonify({"response": {"count": 0, "items": []}})
    elif name == "users.get":
        return jsonify({"response": [{"id": 1, "sex": 2,
                                      "first_name": "Павел",
                                      "last_name": "Дуров",
                                      "bdate": "10.10.1984"}]})
    return jsonify({"error": {"error_code": 3,
                              "error_msg": "Method not found"}})


if __name__ == "__main__":
    app.secret_key = 'IsKollen'
    app.run(host=HOST, port=PORT)
