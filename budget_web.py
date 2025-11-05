from flask import Flask, render_template_string, request, redirect
import json, os, base64, requests

# ----------------------------------------
# ⚙️ Configuration
# ----------------------------------------
DATA_FILE = "/tmp/budget_mensuel.json"
GITHUB_REPO = "j98c9drw9m-jpg/budget-data"  # ⚠️ Mets ici ton dépôt exact
GITHUB_FILE_PATH = "budget_mensuel.json"

app = Flask(__name__)

# ----------------------------------------
# 🔐 Gestion du token GitHub
# ----------------------------------------
def get_github_headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ [DEBUG] GITHUB_TOKEN est vide ou non défini !")
        raise ValueError("❌ GITHUB_TOKEN non défini dans Render")
    else:
        print(f"✅ [DEBUG] GITHUB_TOKEN détecté (longueur = {len(token)})")

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "budget-web-app"
    }

# ----------------------------------------
# ☁️ Lecture et sauvegarde GitHub
# ----------------------------------------
def load_from_github():
    """Télécharge le fichier JSON depuis GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    try:
        r = requests.get(url, headers=get_github_headers())
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8")
            with open(DATA_FILE, "w") as f:
                f.write(content)
            print("✅ Données chargées depuis GitHub.")
        else:
            print(f"⚠️ Aucun fichier trouvé sur GitHub ({r.status_code}). Création d'un nouveau.")
    except Exception as e:
        print("❌ Erreur lors du chargement depuis GitHub :", e)

def save_to_github():
    """Sauvegarde le fichier JSON sur GitHub"""
    try:
        if not os.path.exists(DATA_FILE):
            print("⚠️ Aucun fichier local à sauvegarder.")
            return

        with open(DATA_FILE, "r") as f:
            content = f.read()
        encoded = base64.b64encode(content.encode()).decode("utf-8")

        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        headers = get_github_headers()
        msg = "Update budget data"
        sha = None

        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            sha = r.json()["sha"]

        data = {"message": msg, "content": encoded}
        if sha:
            data["sha"] = sha

        print("🛰️ Envoi vers GitHub :", url)
        r = requests.put(url, headers=headers, json=data)

        if r.status_code in [200, 201]:
            print("💾 Données sauvegardées sur GitHub.")
        else:
            print(f"❌ Erreur lors de la sauvegarde : {r.status_code} {r.text}")

    except Exception as e:
        print("❌ Erreur fatale lors de save_to_github():", e)

# ----------------------------------------
# 💾 Lecture & écriture locale
# ----------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"revenu": 0, "categories": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
    save_to_github()

# ----------------------------------------
# 🖥️ Interface principale
# ----------------------------------------
@app.route("/")
def index():
    data = load_data()
    revenu = data["revenu"]

    categories = []
    total_spent = 0
    for name, cat in data["categories"].items():
        spent = sum(exp["amount"] for exp in cat["expenses"])
        total_spent += spent
        remaining = cat["budget"] - spent
        percent = (spent / cat["budget"] * 100) if cat["budget"] > 0 else 0
        categories.append({
            "name": name,
            "budget": cat["budget"],
            "spent": spent,
            "remaining": remaining,
            "percent": percent
        })

    remaining_global = revenu - total_spent

    html = """
    <html>
    <head>
      <meta charset="utf-8">
      <title>Budget mensuel</title>
      <style>
        body { font-family: Arial; background: #111; color: #eee; margin: 20px; }
        h1, h2 { color: #5ee65a; }
        .box { background: #222; padding: 15px; margin: 10px 0; border-radius: 10px; }
        input, button { padding: 5px; border-radius: 5px; border: none; }
        button { background: #5ee65a; cursor: pointer; margin-top: 5px; }
        a { color: #5ee65a; text-decoration: none; }
        .progress-container { width: 100%; background-color: #333; border-radius: 10px; height: 14px; margin-top: 5px; }
        .progress-bar { height: 14px; border-radius: 10px; transition: width 0.5s; }
      </style>
    </head>
    <body>
      <h1>💰 Mon budget mensuel</h1>
      <p><b>Revenu :</b> {{revenu}} €</p>
      <p><b>Dépensé :</b> {{total_spent}} €</p>
      <p><b>Reste :</b> <span style="color: {{'red' if remaining_global<0 else 'lime'}}">{{remaining_global}} €</span></p>

      <div class="box">
        <h2>Modifier le revenu</h2>
        <form action="/set_income" method="post">
          <input type="text" name="income" placeholder="Revenu (€)" required>
          <button>Mettre à jour</button>
        </form>
      </div>

      <div class="box">
        <h2>Catégories</h2>
        {% for cat in categories %}
          {% set color = 'lime' %}
          {% if cat.remaining / cat.budget < 0.2 %}
            {% set color = 'red' %}
          {% elif cat.remaining / cat.budget < 0.5 %}
            {% set color = 'orange' %}
          {% endif %}
          <p><b>{{cat.name}}</b> — Budget {{cat.budget}} €, Dépensé {{cat.spent}} €</p>
          <div class="progress-container">
            <div class="progress-bar" style="width:{{cat.percent}}%; background-color:{{color}};"></div>
          </div>
          <p>
            <a href="/open/{{cat.name}}">ouvrir</a> |
            <a href="/delete_category/{{cat.name}}" style="color:red;">supprimer</a>
          </p>
        {% endfor %}
        <form action="/add_category" method="post">
          <input name="name" placeholder="Nom catégorie" required>
          <input name="budget" placeholder="Budget (€)" required>
          <button>Ajouter</button>
        </form>
      </div>
    </body></html>
    """
    return render_template_string(html, revenu=revenu, total_spent=total_spent,
                                  remaining_global=remaining_global, categories=categories)

# ----------------------------------------
# 🧾 Routes de gestion
# ----------------------------------------
@app.route("/set_income", methods=["POST"])
def set_income():
    data = load_data()
    try:
        data["revenu"] = float(request.form["income"].replace(",", "."))
    except:
        pass
    save_data(data)
    return redirect("/")

@app.route("/add_category", methods=["POST"])
def add_category():
    data = load_data()
    name = request.form["name"]
    try:
        budget = float(request.form["budget"].replace(",", "."))
    except:
        budget = 0
    data["categories"][name] = {"budget": budget, "expenses": []}
    save_data(data)
    return redirect("/")

@app.route("/delete_category/<name>")
def delete_category(name):
    data = load_data()
    if name in data["categories"]:
        del data["categories"][name]
    save_data(data)
    return redirect("/")

@app.route("/open/<name>")
def open_cat(name):
    data = load_data()
    cat = data["categories"][name]
    spent = sum(exp["amount"] for exp in cat["expenses"])
    remaining = cat["budget"] - spent
    expenses = list(enumerate(cat["expenses"]))

    html = """
    <html><head><meta charset="utf-8"><title>{{name}}</title>
    <style>
      body { font-family: Arial; background:#111; color:#eee; margin:20px;}
      .box{background:#222;padding:15px;margin:10px 0;border-radius:10px;}
      input,button{padding:5px;border:none;border-radius:5px;}
      button{background:#5ee65a;cursor:pointer;margin-top:5px;}
      a{color:#5ee65a;text-decoration:none;}
    </style></head><body>
      <a href="/">← Retour</a>
      <h1>{{name}}</h1>
      <p>Budget : {{cat.budget}} € — Dépensé : {{spent}} € — Reste :
         <b style="color:{{'red' if remaining<0 else 'lime'}}">{{remaining}} €</b></p>

      <div class="box">
        <h2>Ajouter une dépense</h2>
        <form action="/add_expense/{{name}}" method="post">
          <input name="label" placeholder="Nom dépense" required>
          <input name="amount" placeholder="Montant (€)" required>
          <button>Ajouter</button>
        </form>
      </div>

      <div class="box">
        <h2>Dépenses</h2>
        {% for i, exp in expenses %}
          <p>- {{exp.name}} : {{exp.amount}} €
          (<a href="/delete_expense/{{name}}/{{i}}" style="color:red;">supprimer</a>)</p>
        {% endfor %}
      </div>
    </body></html>
    """
    return render_template_string(html, name=name, cat=cat, spent=spent, remaining=remaining, expenses=expenses)

@app.route("/add_expense/<name>", methods=["POST"])
def add_expense(name):
    data = load_data()
    label = request.form["label"]
    try:
        amount = float(request.form["amount"].replace(",", "."))
    except:
        amount = 0
    data["categories"][name]["expenses"].append({"name": label, "amount": amount})
    save_data(data)
    return redirect(f"/open/{name}")

@app.route("/delete_expense/<name>/<int:index>")
def delete_expense(name, index):
    data = load_data()
    del data["categories"][name]["expenses"][index]
    save_data(data)
    return redirect(f"/open/{name}")

# ----------------------------------------
# 🚀 Lancement
# ----------------------------------------
if __name__ == "__main__":
    print("🚀 Lancement de l'application Flask...")

    # Recharge les données depuis GitHub à chaque redémarrage
    load_from_github()

    # Si le fichier local a disparu (Render a vidé /tmp), on le recrée à partir du GitHub
    if not os.path.exists(DATA_FILE):
        print("⚠️ Fichier introuvable, création d’un nouveau budget local à partir de GitHub...")
        save_to_github()

    # Lancement du serveur Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
