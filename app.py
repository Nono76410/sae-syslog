import os
import chromadb
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# --- Initialisation de ChromaDB (en local dans le dossier ./chroma_db) ---
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="network_docs")


def index_knowledge_base():
  """Indexe les fichiers texte de la base de connaissances dans ChromaDB"""
  kb_dir = "knowledge_base"
  if not os.path.exists(kb_dir):
    return

  doc_id = 0
  for vendor in os.listdir(kb_dir):
    vendor_path = os.path.join(kb_dir, vendor)
    if os.path.isdir(vendor_path):
      for filename in os.listdir(vendor_path):
        if filename.endswith(".txt"):
          file_path = os.path.join(vendor_path, filename)
          with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Découpage simple par paragraphe ou bloc
            chunks = [
                c.strip() for c in content.split("\n\n") if c.strip()
            ]
            for chunk in chunks:
              collection.upsert(
                  documents=[chunk],
                  metadatas=[{"vendor": vendor, "source": filename}],
                  ids=[f"doc_{doc_id}"],
              )
              doc_id += 1


# Indexer la doc au démarrage du serveur
index_knowledge_base()


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_log():
  data = request.get_json()
  raw_log = data.get("log", "").strip()

  if not raw_log:
    return jsonify({"error": "Aucun log fourni"}), 400

  # --- Recherche RAG : Interroger ChromaDB avec le log collé ---
  results = collection.query(
      query_texts=[raw_log],
      n_results=1,  # Récupère l'extrait de doc le plus pertinent
  )

  relevant_doc = "Aucune documentation spécifique trouvée."
  vendor_detected = "Inconnu"

  if results["documents"] and results["documents"][0]:
    relevant_doc = results["documents"][0][0]
    vendor_detected = results["metadatas"][0][0].get("vendor", "Inconnu")

  # --- Analyse simulée (qu'on branchera sur un vrai LLM local/API juste après) ---
  analysis_result = {
      "log_recu": raw_log,
      "equipement_detecte": vendor_detected.capitalize(),
      "explication": (
          f"Analyse basée sur la base de connaissances pour un équipement"
          f" {vendor_detected}."
      ),
      "criticite": "Attention / Élevée",
      "doc_associee": relevant_doc,
  }

  return jsonify(analysis_result)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)