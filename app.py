from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/analyze", methods=["POST"])
def analyze_log():
    data = request.get_json()
    raw_log = data.get("log", "").strip()
    
    if not raw_log:
        return jsonify({"error": "Aucun log fourni"}), 400

    # TODO: Ici on branchera ChromaDB et l'IA pour analyser le log
    # Pour l'instant, on simule une réponse pour voir si le copier-coller fonctionne
    analysis_result = {
        "log_recu": raw_log,
        "equipement_detecte": "Cisco (Simulé)",
        "explication": "Ceci est une analyse simulée de ton log collé.",
        "criticite": "Moyenne",
        "doc_associee": "Extrait de la documentation constructeur..."
    }

    return jsonify(analysis_result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)