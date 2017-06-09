from flask import Flask, url_for, request, render_template, redirect
import sqlite3 as db
import json
from pymystem3 import Mystem
from operator import itemgetter
from requests import request as req
from itertools import chain
import string
from nltk.corpus import movie_reviews




app = Flask(__name__)


punc = set(chain.from_iterable(string.punctuation))
twcorp = movie_reviews

def make_vk_api_request(method, **kwargs):
    string = "http://api.vk.com/method/" + method + "?" + "&".join(["%s=%s" % (str(k), str(v)) for k, v in kwargs.items()])
    return json.loads(req("GET", string).text)
# region routes


@app.route('/')
def index():
    index_routes = {"A dumb poll about dogs and cats": url_for("dogpoll"),
                    "An utility that displays Russian text verb info": url_for("verbinfo"),
                    "An utility for getting word frequency lists from vk posts":url_for("vkgroupinfo"),
                    "A tool that displays some positive or negative contexts for a word":url_for("nltkinfo")}
    return render_template("mainpage.jinja2", index_routes=index_routes)


@app.route("/dogpoll")
def dogpoll():
    return render_template("dogpoll.jinja2")


@app.route("/proc_dogpoll")
def proc_dogpoll():
    username = request.args["username"]
    if username == '':
        username = "Anon"
    database = db.connect("prog_3.sqlite")
    cursor = database.cursor()
    cursor.execute("INSERT INTO Dogtest (user, reply) VALUES (?, ?)", (username, request.args["reply"]))
    database.commit()
    losers = cursor.execute("SELECT * FROM Dogtest WHERE reply='Cats'")
    loser_users = [row[1] for row in losers]
    winners = cursor.execute("SELECT *  FROM Dogtest WHERE reply='Dogs'")
    winner_users = [row[1] for row in winners]
    return render_template("dogpoll_reply.jinja2", Reply=request.args["reply"], Losers=loser_users, Winners=winner_users)


@app.route("/verbinfo")
def verbinfo():
    # if not request.args.get("res"):
    #     res = {}
    # else:
    res = sorted(json.loads(request.args.get("res", "{}")).items(), key=itemgetter(1), reverse=True)
    text = request.args.get("text", "")

    # if not request.args.get("counts"):
    #     counts = {}
    # else:
    counts = sorted(json.loads(request.args.get("counts", "{}")).items(), key=itemgetter(1), reverse=True)
    return render_template("verb_info.jinja2", Result=res, Text=text, Counts=counts)


@app.route("/proc_verbinfo")
def proc_verbinfo():
    stringu = request.args.get("res")
    m = Mystem()
    ana = m.analyze(stringu)
    verbs = [x for x in ana if 'analysis' in x and len(x["analysis"]) >0 and "gr" in x["analysis"][0] and "V" in x['analysis'][0]['gr'].split("=")[0].split(',')]
    res = {"Perfective": 0, "Imperfective": 0, "Transitive": 0, "Intransitive": 0, "Total": len(verbs)}
    counts = {}
    for v in verbs:
        gram = v['analysis'][0]['gr']
        lex = v['analysis'][0]['lex']
        counts[lex] = counts.get(lex, 0) + 1

        gram_chunks = list(chain.from_iterable([x.split(",") for x in gram.split("=")]))
        if "нп" in gram_chunks:
            res["Intransitive"] += 1
        else:
            res["Transitive"] += 1
        if "сов" in gram_chunks:
            res["Perfective"] += 1
        elif "несов" in gram_chunks:
            res["Imperfective"] += 1

    return redirect(url_for("verbinfo", res=json.dumps(res), counts=json.dumps(counts), text=stringu))


@app.route("/vkgroupinfo")
def vkgroupinfo():
    sort_c = sorted(json.loads(request.args.get("counts", "{}")).items(), key=itemgetter(1), reverse=True)[:100]
    return render_template("vkgroupinfo.jinja2", group_id=request.args.get("group_id", ""), counts=sort_c)


@app.route("/proc_vkgroupinfo")
def proc_vkgroupinfo():
    m = Mystem()
    group_id = request.args.get("group_id")
    first = make_vk_api_request("wall.get", owner_id="-"+(group_id), count=1)
    if "response" in first:
        id = first["response"][1]["id"]
        if int(id) > 1000:
            start_id = id - 1000
        else:
            start_id = 0

        response = [make_vk_api_request("wall.getById", posts="-"+group_id+ "_" +str(x))["response"] for x in range(start_id, int(id))]
        response = [x[0].get("text", "") for x in response if len(x)==1]
        lemmas = list(chain.from_iterable([m.lemmatize(x) for x in response]))
        counts = {}
        for i in lemmas:
            if i.strip() not in punc and i.strip() != "":
                counts[i] = counts.get(i, 0) + 1
        return redirect(url_for("vkgroupinfo", group_id=group_id, counts=json.dumps(counts)))
    elif "error" in first:
        return redirect(url_for("vkgroupinfo", group_id=group_id, counts=json.dumps({"Cannot access group":first["error"]["error_msg"]})))


@app.route("/nltkinfo")
def nltkinfo():
    contexts = json.loads(request.args.get("contexts", '{"positive": [], "negative": []}'))
    data = bool(request.args.get("hasdata", None))

    return render_template("nltkinfo.jinja2", Context = {"positive":contexts["positive"][:5], "negative":contexts["negative"][:5]}, Counts=(len(contexts["positive"]), len(contexts["negative"])), Hasdata=data)


@app.route("/proc_nltkinfo")
def proc_nltkinfo():
    word = request.args.get("word")
    context = {"positive":[], "negative":[]}
    for uid in twcorp.fileids("neg"):
        for sent in twcorp.sents(uid):
            if word in sent:
                context["negative"].append(" ".join(sent))

    for uid in twcorp.fileids("pos"):
        for sent in twcorp.sents(uid):
            if word in sent:
                context["positive"].append(" ".join(sent))

    return redirect(url_for("nltkinfo", contexts=json.dumps(context), hasdata="True"))







# endregion routes




if __name__ == '__main__':
    app.run(debug=True)
