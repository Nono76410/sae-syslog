import json
import os
import time
import chromadb
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai.errors import APIError

app = Flask(__name__)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="network_docs")

client = genai.Client()


def index_knowledge_base():
  """Indexe les fichiers texte du dossier knowledge_base/ dans ChromaDB."""
  kb_dir = "knowledge_base"
  if not os.path.exists(kb_dir):
    os.makedirs(kb_dir)
    return

  doc_id = 0
  for root, _, files in os.walk(kb_dir):
    for file in files:
      if file.endswith(".txt"):
        file_path = os.path.join(root, file)
        vendor = os.path.basename(root)
        with open(file_path, "r", encoding="utf-8") as f:
          content = f.read()
          chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
          for chunk in chunks:
            collection.upsert(
                documents=[chunk],
                metadatas=[{"vendor": vendor, "file": file}],
                ids=[f"doc_{doc_id}"],
            )
            doc_id += 1


index_knowledge_base()


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
  data = request.get_json()
  raw_log = data.get("log", "").strip()

  if not raw_log:
    return jsonify({"error": "Aucun log fourni"}), 400

  results = collection.query(query_texts=[raw_log], n_results=1)

  extracted_doc = "Aucune documentation spécifique trouvée dans la base."
  source_file = "Documentation Générale"

  if results["documents"] and results["documents"][0]:
    extracted_doc = results["documents"][0][0]
    source_file = results["metadatas"][0][0].get("file", "Inconnue")

  # Step B: Construction du Prompt Structuré
  prompt = f"""
Tu es un expert en ingénierie réseau pour l'entreprise Linkt.
Analyse le log brut ci-dessous en t'appuyant sur l'extrait de documentation fourni si pertinent.

EXTRAIT DE DOCUMENTATION CONSTRUCTEUR :
{extracted_doc}

LOG BRUT À ANALYSER :
{raw_log}

RÉPONDS STRICTEMENT AU FORMAT JSON avec les clés exactes suivantes :
- "explication": Explication claire de la cause racine du log en français.
- "solution": Procédure corrective étape par étape pour le technicien support.
- "criticite": Niveau de gravité (Faible, Moyenne, Élevée, Critique).
- "source": Nom du constructeur ou de la doc d'origine.
"""

  modeles_a_tester = ["gemini-3.8-flash", "gemini-2.5-flash-lite"]
  response_text = None

  try:
    for model_name in modeles_a_tester:
      for tentative in range(3):
        try:
          response = client.models.generate_content(
              model=model_name, contents=prompt
          )
          response_text = response.text.strip()
          break
        except APIError as e:
          if e.code == 503:
            time.sleep(2)
            continue
          else:
            raise e
      if response_text:
        break

    if not response_text:
      raise Exception("Les serveurs sont actuellement saturés.")

    cleaned_response = response_text
    if cleaned_response.startswith("```json"):
      cleaned_response = cleaned_response[7:-3].strip()

    result_json = json.loads(cleaned_response)
    result_json["fichier_source"] = source_file
    return jsonify(result_json)

  except Exception as e:
    return (
        jsonify({
            "explication": "Erreur lors de la génération de l'analyse.",
            "solution": str(e),
            "criticite": "Erreur",
            "source": "Système",
            "fichier_source": source_file,
        }),
        500,
    )


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)