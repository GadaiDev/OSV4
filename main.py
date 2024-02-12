import glob
import hashlib
import os
import random
import re
import time
from datetime import datetime
from threading import Thread
import pytz
from flask import Flask, redirect, render_template, request, send_file, url_for
from flask_socketio import SocketIO
from urllib import request as rqurlapi
emoji_pattern = re.compile(
    "["
    u"\U0001F600-\U0001F64F"  # スマイル絵文字
    u"\U0001F300-\U0001F5FF"  # シンボル
    u"\U0001F680-\U0001F6FF"  # 車や建物
    u"\U0001F700-\U0001F77F"  # 音符
    u"\U0001F780-\U0001F7FF"  # フラッグ
    u"\U0001F800-\U0001F8FF"  # その他
    u"\U0001F900-\U0001F9FF"  # 顔
    u"\U0001FA00-\U0001FA6F"  # スポーツ
    u"\U0001FA70-\U0001FAFF"  # 食べ物
    u"\U0001F004-\U0001F0CF"  # 追加の絵文字
    u"\U0001F200-\U0001F251"  # 装飾記号
    "]+",
    flags=re.UNICODE)
# テキストからURLを検出する正規表現パターン
url_pattern = r'(https?://\S+)'
counter = 0
pv = {}
aku = {}

def process_imgur_url(url):
  imgur_pattern = re.compile(r'^https?://(?:i\.)?imgur\.com/([a-zA-Z0-9]+)(?:\.\w+)?$')

  match = imgur_pattern.match(url)
  if match:
    img_id = match.group(1)
    img_tag = f'<img src="https://i.imgur.com/{img_id}.png" alt="Imgur Image">'
    return img_tag
  else:
    a_tag = f'<a href="{url}" target="_blank">{url}</a>'
    return a_tag


def count(path):
  a = str(int(open(path, "r").read()) + 1)
  open(path, "w").write(a)
  return open(path, "r").read()


def get_japantime():
  japan_tz = pytz.timezone('Asia/Tokyo')
  return str(datetime.now(japan_tz)).replace("+09:00","")


app = Flask(__name__)
skio = SocketIO(app)

@app.route('/')
def index():
  return render_template('index.html')
@app.route("/updatetuuti", methods=["POST"])
def updatetuuti():
  skio.emit("update_information",request.form.get("text"))
  return redirect("/admin/update")
@app.route("/admin/update")
def update():
  return send_file("updategamen.html")
@app.route("/bbs/<bbs>")
def bbspage(bbs):
  hoge = ""
  p = glob.glob(f"bbs/{bbs}/*/")
  for i in p:
    url = i.replace(f"bbs/{bbs}/", "").replace("/", "")
    try:
      threadtitle = open(f"{i}title.txt", "r").read()
      threadcount = open(f"{i}count.txt", "r").read()
      hoge += f"<a href=\"/test/read.cgi/{bbs}/{url}/\">{threadtitle}({threadcount})</a><br>\n"
    except FileNotFoundError:
      pass
  if len(p) == 0:
    hoge = "<p style='text-align:center'>ないみたい</p>"
  return render_template(
      "bbs.html",
      bbsname=open(f"bbs/{bbs}/title.txt", "r").read(),
      bbsdesc=open(f"bbs/{bbs}/description.txt", "r").read(),
      bbsid=bbs,
  ).replace("<!-- bbsthread -->", hoge)

@app.route('/test/read.cgi/<bbs>/<thread>/')
def page(bbs, thread):
  key = f'{bbs}/{thread}'
  if key in pv:
    pv[key] += 1
  else:
    pv[key] = 1
  threads = render_template('bbs_thread.html',
                            threadtitle=open(f"bbs/{bbs}/{thread}/title.txt",
                                             "r").read(),
                            bbs=bbs,
                            thread=thread,
                            pv=pv[key])
  threads = threads.replace(
      "<!-- messages -->",
      re.sub(
          r"＞＞([0-9]*)",
          r"<a href='/test/read.cgi/" + bbs + "/" + thread + r"/\1'>＞＞\1</a>",
          re.sub(
              url_pattern, r"<a href='\1' target='_blank' rel='noopener noreferrer'>\1</a>",
              open(f"bbs/{bbs}/{thread}/dat.txt",
                   "r").read().replace("\n", "<br>\n"))))
  return threads.replace("�","\0")


@app.route('/test/read.cgi/<bbs>/<thread>/<num>')
def page2(bbs, thread, num):
  threads = render_template(
      'bbs_thread.html',
      threadtitle=open(f"bbs/{bbs}/{thread}/title.txt", "r").read(),
      bbs=bbs,
      thread=thread,
  )
  threads = threads.replace(
      "<!-- messages -->",
      re.sub(
          r"＞＞([0-9]*)",
          r"<a href='/test/read.cgi/" + bbs + "/" + thread + r"/\1'>＞＞\1</a>",
          re.sub(
              url_pattern, r"<a href='\1' target='_blank' rel='noopener noreferrer'>\1</a>",
              open(f"bbs/{bbs}/{thread}/dat.txt",
                   "r").read().split("\n\0\n")[int(num) - 1].replace(
                       "\n", "<br>\n"))))
  return threads.replace("�","\0")


@skio.on("post")
def handle_post(data):
  username = data["name"].replace("<", "＜").replace(">",
                                                    "＞").replace("\n", "\n　　")
  message = data['msg'].replace("<", "＜").replace(">",
                                                  "＞").replace("\n", "\n　　")
  mails = data["mail"]
  nusi = False
  
  communityNote = False
  if data["id"] == "":
    ids = "とくさん"
  else:
    ids = "".join(list(hashlib.md5(data["id"].encode()).hexdigest())[0:12])
  
  if username == "CommunityNote":
    username = "<font color='blue'>CommunityNote</font>"
    message = message.replace('\n　　','\n')
    communityNote = True
  #ここにコマンドを追加する
  
  if username == "":
    username = "名無し@OSV4"
  
  if not ids == "とくさん":
    itchi = open(f"bbs/{data['bbs']}/{data['threads']}/dat.txt","r",encoding="utf-8").read().split("\n\0\n")[0]
    itchiID = re.findall(r"""[0-9]{1,100}:名前: .+ [0-9]+-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}\+[0-9]{2}:[0-9]{2} ID:([0-9a-fあ-ん]+)\n　　.+""",itchi)
    if ids == itchiID[0]:
      username+="<small><small><font color='red'>主</font></small></small>"
  color = "green"
  if "!kintama" in username:
    color = "yellow"
    username.replace("!kintama", "", 1)
  if username == "OSV5Mirai":
    username = f"名無し@OSV5"
  if "!API" in message:
    apicom = re.sub(r"!API:\"(https?://\S+)\"",r"\1",message)
    try:
      message+=f"\n　　\n　　<font color=\"red\">API:</font>"+rqurlapi.urlopen(apicom).read().decode().replace("<", "＜").replace(">","＞").replace("\n", "\n　　")
    except:
      message+=f"\n　　\n　　<font color=\"red\">API:エラー。</font>"
  
  if len(re.findall(r"[ぁ-ンー0-9a-zA-Z一-鿿ｱ-ﾝ]+", message)) > 0: #ここで空白文字を規制する
    c = count(f"bbs/{data['bbs']}/{data['threads']}/count.txt")
    if communityNote:
      open(f"bbs/{data['bbs']}/{data['threads']}/dat.txt", "a").write(f"""<div class="card" style="width:80%"><div class="card-header">
    {c}:閲覧したユーザーが役に立つ背景情報を追加しました
  </div>
  <div class="card-body">
{message}
  </div>
  <div class="card-footer" style="color:blue">
    役に立ちましたか？
  </div></div>\n\0\n""")
    else:
      open(f"bbs/{data['bbs']}/{data['threads']}/dat.txt", "a").write(
          f"""<a onclick="addanker(c)">{c}</a>:名前: <b><font color='{color}'>{username}</font></b> {get_japantime()} ID:{ids}\n　　{message}\n\0\n"""
      )
    skio.emit(
        f"get-{data['bbs']}-{data['threads']}",
        re.sub(
            r"＞＞([0-9]*)", r"<a href='/test/read.cgi/" + data['bbs'] + "/" +
            data['threads'] + r"/\1'>＞＞\1</a>",
            re.sub(
                url_pattern, r"<a href='\1'>\1</a>",
                open(f"bbs/{data['bbs']}/{data['threads']}/dat.txt",
                     "r").read().replace("\n", "<br>\n"))).replace("�","\1"))


@app.route('/post_register/<bbs>/', methods=['POST'])
def post2_message(bbs):

  thread = "".join([
      random.choice(
          "1234567890aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ")
      for i in range(32)
  ])
  os.mkdir(f"bbs/{bbs}/{thread}/")
  username = request.form['username'].replace("<", "＜").replace(">", "＞")
  if request.form["ids"] == "":
    ids = "とくさん"
  else:
    ids = "".join(
        list(hashlib.md5(request.form["ids"].encode()).hexdigest())[0:12])
  mails = request.form['mail']
  ## ここに「sage」などのコマンドを追加する

  
  if username == "":
    username = "名無しさん"
  color = "green"
  if "!kintama" in username:
    color = "yellow"
    username.replace("!kintama", "", 1)
  username.replace("★", "☆")
  title = request.form['title'].replace("<",
                                        "＜").replace(">",
                                                     "＞").replace("\n", "")

  message = request.form['message'].replace("<", "＜").replace(">",
                                                              "＞").replace(
                                                                  "\n", "\n　　")
  open(f"bbs/{bbs}/{thread}/dat.txt", "a").write(
      f"""1:名前: <b><font color='{color}'>{username}</font></b> {get_japantime()} ID:{ids}\n　　{message}\n\0\n"""
  )
  open(f"bbs/{bbs}/{thread}/title.txt", "w").write(title)
  open(f"bbs/{bbs}/{thread}/count.txt", "w").write("1")
  Thread(target=lambda: (deletethreads(bbs, thread))).start()

  return redirect(url_for('page', bbs=bbs, thread=thread))


@skio.on('connect')
def handle_connects():
  global counter
  counter += 1
  skio.emit('update_counter', {'count': counter})


@skio.on('disconnect')
def handle_disconnects():
  global counter
  counter -= 1
  skio.emit('update_counter', {'count': counter})


@app.route("/bbslist.htm")
def bbslist():
  r = ""
  for i in glob.glob("bbs/*"):
    url = i.replace("bbs/", "")
    title = open(f"{i}/title.txt","r")
    r += f"<a href=\"bbs/{url}\">{title.read()}</a><br>\n"
  return render_template("bbslist.html").replace("<!-- r -->", r)


@app.route("/<bbs>/dat/<fname>")
def robots(bbs, fname):
  kak = fname.split(".")[1]
  fname = fname.split(".")[0]
  if kak == "dat":
    return send_file(f"bbs/{bbs}/{fname}/dat.txt")
  elif kak == "ttl":
    return send_file(f"bbs/{bbs}/{fname}/title.txt")
  elif kak == "cnt":
    return send_file(f"bbs/{bbs}/{fname}/count.txt")
  else:
    return "?"

@app.route('/bbsmake/', methods=['POST'])
def gadai():
  bbs = request.form['name'].replace("<", "＜").replace(">", "＞")
  bbsid = request.form['id'].replace("<", "＜").replace(">", "＞")
  desc = request.form['desc'].replace("<", "＜").replace(">", "＞")
  if not os.path.exists(f"bbs/{bbsid}/"):
    os.mkdir(f"bbs/{bbsid}/")
    open(f"bbs/{bbsid}/title.txt", "w").write(bbs)
    open(f"bbs/{bbsid}/description.txt", "w").write(desc)
    return redirect(f"/bbs/{bbsid}")
  else:
    return "もうその掲示板は存在するみたい。"


@app.route("/admin/delete/<bbs>/<thread>/")
def admins(bbs, thread):
  if request.args["password"] == open("password.txt", "r").read(): #パスワードは自分で設定してね
    try:
      os.remove(f"bbs/{bbs}/{thread}/title.txt")
    except FileNotFoundError:
      pass
    try:
      os.remove(f"bbs/{bbs}/{thread}/dat.txt")
    except FileNotFoundError:
      pass
    try:
      os.remove(f"bbs/{bbs}/{thread}/count.txt")
    except FileNotFoundError:
      pass
    os.rmdir(f"bbs/{bbs}/{thread}/")
    return redirect(f"/bbs/{bbs}")
  else:
    return "不正ログインやめてね。"

@app.route("/robots.txt")
def robotstxt():
  return """User-agent: *
Disallow: /bbslist.htm
Disallow
Allow: /test/read.cgi/
"""



if __name__ == '__main__':
  skio.run(app, "0.0.0.0", port=8000, debug=True, allow_unsafe_werkzeug=True)
