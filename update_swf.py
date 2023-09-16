import requests, json

with open("static/client/versions/versions.json", "r") as f:
    versions = json.load(f)
link = "http://cdn-sp.tortugasocial.com/tropicania-ru/"
for file in versions:
    name = file.replace(".swf", "") + "_" + versions[file] + ".swf"
    with open(f"new/{name}", "wb") as g:
        g.write(requests.get(link+name, verify=False).content)
    print(file)