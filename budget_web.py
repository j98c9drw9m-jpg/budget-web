from flask import Flask, render_template_string, request, redirect
import json, os

DATA_FILE = "budget_mensuel.json"
app = Flask(__name__)

# Charger et sauvegarder les données
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"revenu": 0, "categories": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- Page principale ---
@app.route("/")
def index():
    data = load_data()
    revenu = data["revenu"]
    total_spent = sum(sum(exp["amount"] for exp in cat["expenses"]) for cat in data["categories"].values())
    remaining = revenu - total_spent

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
      </style>
    </head>
    <body>
      <h1>💰 Mon budget mensuel</h1>
      <p><b>Revenu mensuel :</b> {{revenu}} €</p>
      <p><b>Dépensé :</b> {{total_spent}} €</p>
      <p><b>Reste :</b> <span style="color: {{'red' if remaining<0 else 'lime'}}">{{remaining}} €</span></p>
      <div class="box">
        <h2>Modifier le revenu</h2>
        <form action="/set_income" method="post">
          <input type="text" name="income" placeholder="Revenu (€)" required>
          <button>Mettre à jour</button>
        </form>
      </div>
      <div class="box">
        <h2>Catégories</h2>
        {% for name, cat in data["categories"].items() %}
          <p><b>{{name}}</b> — Budget {{cat["budget"]}} €, 
          Dépensé {{sum(exp["amount"] for exp in cat["expenses"])}} €
          (<a href="/open/{{name}}">ouvrir</a>)</p>
        {% endfor %}
        <form action="/add_category" method="post">
          <input name="name" placeholder="Nom catégorie" required>
          <input name="budget" placeholder="Budget (€)" required>
          <button>Ajouter</button>
        </form>
      </div>
    </body></html>
    """
    return render_template_string(html, data=data, revenu=revenu, total_spent=total_spent, remaining=remaining)

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

@app.route("/open/<name>")
def open_cat(name):
    data = load_data()
    cat = data["categories"][name]
    spent = sum(exp["amount"] for exp in cat["expenses"])
    remaining = cat["budget"] - spent

    html = """
    <html><head><meta charset="utf-8"><title>{{name}}</title>
    <style>body { font-family: Arial; background:#111; color:#eee; margin:20px;}
    .box{background:#222;padding:15px;margin:10px 0;border-radius:10px;}
    input,button{padding:5px;border:none;border-radius:5px;}
    button{background:#5ee65a;cursor:pointer;margin-top:5px;}
    a{color:#5ee65a;text-decoration:none;}
    </style></head><body>
      <a href="/">← Retour</a>
      <h1>{{name}}</h1>
      <p>Budget : {{cat["budget"]}} € — Dépensé : {{spent}} € — Reste : <b style="color:{{'red' if remaining<0 else 'lime'}}">{{remaining}} €</b></p>
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
        {% for i, exp in enumerate(cat["expenses"]) %}
          <p>- {{exp["name"]}} : {{exp["amount"]}} € 
          (<a href="/delete_expense/{{name}}/{{i}}">supprimer</a>)</p>
        {% endfor %}
      </div>
    </body></html>
    """
    return render_template_string(html, name=name, cat=cat, spent=spent, remaining=remaining)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)