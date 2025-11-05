from flask import Flask, render_template_string, request, redirect
import json, os

# ----------------------------------------
# Configuration générale
# ----------------------------------------
DATA_FILE = "/tmp/budget_mensuel.json"
app = Flask(__name__)

# ----------------------------------------
# Gestion du stockage JSON
# ----------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"revenu": 0, "categories": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ----------------------------------------
# Page principale : résumé global
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
      <title>💰 Mon budget mensuel</title>
      <style>
        body { font-family: Arial, sans-serif; background: #111; color: #eee; margin: 30px; }
        h1, h2 { color: #5ee65a; }
        .box { background: #222; padding: 15px; margin: 20px 0; border-radius: 10px; }
        input, button { padding: 6px; border-radius: 6px; border: none; }
        button { background: #5ee65a; cursor: pointer; margin-top: 6px; }
        button:hover { background: #4ed64a; }
        a { color: #5ee65a; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .inline-links a { margin-right: 10px; }

        /* Barre de progression */
        .progress-container {
          width: 100%;
          background-color: #333;
          border-radius: 10px;
          margin-top: 5px;
          height: 14px;
        }
        .progress-bar {
          height: 14px;
          border-radius: 10px;
          transition: width 0.5s;
        }

        .small-text { font-size: 0.9em; color: #aaa; }
      </style>
      <script>
        function confirmDeleteCategory(name) {
          return confirm('Supprimer la catégorie "' + name + '" ? Toutes les dépenses associées seront effacées.');
        }
      </script>
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
        {% if categories %}
          {% for cat in categories %}
            {% set ratio = (cat.remaining / cat.budget) if cat.budget > 0 else 1 %}
            {% set color = 'lime' %}
            {% if ratio < 0.2 %}
              {% set color = 'red' %}
            {% elif ratio < 0.5 %}
              {% set color = 'orange' %}
            {% endif %}
            <p><b>{{cat.name}}</b> — Budget {{cat.budget}} €, Dépensé {{cat.spent}} €</p>
            <div class="progress-container">
              <div class="progress-bar" style="width:{{cat.percent}}%; background-color:{{color}};"></div>
            </div>
            <div class="inline-links small-text">
              <a href="/open/{{cat.name}}">🔍 ouvrir</a> |
              <a href="/delete_category/{{cat.name}}" onclick="return confirmDeleteCategory('{{cat.name}}')" style="color:red;">🗑️ supprimer</a>
            </div>
            <hr style="border: none; border-bottom: 1px solid #333; margin: 15px 0;">
          {% endfor %}
        {% else %}
          <p>Aucune catégorie pour le moment.</p>
        {% endif %}
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
# Modification du revenu
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

# ----------------------------------------
# Ajout / suppression de catégories
# ----------------------------------------
@app.route("/add_category", methods=["POST"])
def add_category():
    data = load_data()
    name = request.form["name"].strip()
    if not name:
        return redirect("/")
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

# ----------------------------------------
# Détails d'une catégorie
# ----------------------------------------
@app.route("/open/<name>")
def open_cat(name):
    data = load_data()
    if name not in data["categories"]:
        return redirect("/")
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
      a:hover{text-decoration:underline;}
    </style>
    <script>
      function confirmDeleteExpense(label) {
        return confirm('Supprimer la dépense "' + label + '" ?');
      }
    </script>
    </head><body>
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
        {% if expenses %}
          {% for i, exp in expenses %}
            <p>- {{exp.name}} : {{exp.amount}} €
            (<a href="/delete_expense/{{name}}/{{i}}" onclick="return confirmDeleteExpense('{{exp.name}}')" style="color:red;">🗑️ supprimer</a>)</p>
          {% endfor %}
        {% else %}
          <p>Aucune dépense enregistrée.</p>
        {% endif %}
      </div>
    </body></html>
    """
    return render_template_string(html, name=name, cat=cat, spent=spent,
                                  remaining=remaining, expenses=expenses)

# ----------------------------------------
# Gestion des dépenses
# ----------------------------------------
@app.route("/add_expense/<name>", methods=["POST"])
def add_expense(name):
    data = load_data()
    if name not in data["categories"]:
        return redirect("/")
    label = request.form["label"].strip()
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
    if name in data["categories"]:
        if 0 <= index < len(data["categories"][name]["expenses"]):
            del data["categories"][name]["expenses"][index]
            save_data(data)
    return redirect(f"/open/{name}")

# ----------------------------------------
# Lancement de l'application
# ----------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))