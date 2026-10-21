import json
import os
import re
import time
import chromadb
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai.errors import APIError
import requests

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="network_docs")

# 2. Initialisation du client Gemini
client = genai.Client()


def anonymize_log(log_text):
    """Masque uniquement les IPv4 dans la plage 198.18.0.0/15 (198.18.x.x et 198.19.x.x)."""
    ip_specific_pattern = r'\b198\.(?:18|19)\.[0-9]{1,3}\.[0-9]{1,3}\b'
    anonymized = re.sub(ip_specific_pattern, '[IP_MASQUÉE]', log_text)
    return anonymized


def query_ollama(prompt):
    """Interroge le modèle Ollama local."""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        res = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json().get("response", "").strip()
    except Exception as e:
        print(f"[Ollama Error] : {e}")
        return None
    return None


def query_gemini(prompt):
    """Interroge l'API Gemini Cloud avec gestion du retry."""
    modeles_a_tester = ["gemini-3.8-flash", "gemini-2.5-flash-lite"]
    for model_name in modeles_a_tester:
        for _ in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name, contents=prompt
                )
                return response.text.strip()
            except APIError as e:
                if e.code == 503:
                    time.sleep(2)
                    continue
                else:
                    raise e
    return None


def save_learned_log(raw_log, result_json):
    """Enregistre les requêtes traitées par Gemini dans la base de connaissances locale."""
    learned_dir = "knowledge_base/gemini_learned"
    if not os.path.exists(learned_dir):
        os.makedirs(learned_dir)
        
    file_path = os.path.join(learned_dir, "gemini_learned_logs.txt")
    
    nouveau_bloc = f"""
-------------------------------------------------------------------

[MESSAGE CODE] {raw_log.strip()}
- Description : {result_json.get('explication', 'Non spécifiée')}
- Cause Racine : Identifiée automatiquement via Gemini Cloud.
- Diagnostic : Se référer au log brut ci-dessus.
- Solution Corrective : 
  1. {result_json.get('solution', 'Non spécifiée')}
"""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(nouveau_bloc)


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

                    chunks = [
                        c.strip()
                        for c in content.split("-------------------------------------------------------------------")
                        if c.strip()
                    ]

                    if len(chunks) <= 1:
                        chunks = [c.strip() for c in content.split("\n\n") if c.strip()]

                    for chunk in chunks:
                        collection.upsert(
                            documents=[chunk],
                            metadatas=[{"vendor": vendor, "file": file}],
                            ids=[f"doc_{doc_id}"],
                        )
                        doc_id += 1

# Indexation au lancement
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
    has_local_doc = False

    if results["documents"] and results["documents"][0]:
        extracted_doc = results["documents"][0][0]
        source_file = results["metadatas"][0][0].get("file", "Inconnue")
        has_local_doc = True

    response_text = None
    engine_used = "Ollama (Local)"

    if has_local_doc:
        prompt_local = f"""
Tu es un expert en ingénierie réseau pour Linkt.
Analyse le log suivant en t'appuyant sur la documentation fournie.

DOC CONSTRUCTEUR:
{extracted_doc}

LOG À ANALYSER:
{raw_log}

RÉPONDS STRICTEMENT AU FORMAT JSON avec ces 4 clés exactes (sans texte autour) :
{{
  "explication": "...",
  "solution": "...",
  "criticite": "Faible/Moyenne/Élevée/Critique",
  "source": "Constructeur"
}}
"""
        response_text = query_ollama(prompt_local)

    if not response_text or "UNKNOWN" in response_text:
        engine_used = "Gemini Cloud (Anonymisé)"
        anonymized_log = anonymize_log(raw_log)

        prompt_cloud = f"""
Tu es un expert en ingénierie réseau pour l'entreprise Linkt.
Analyse le log anonymisé ci-dessous.

EXTRAIT DE DOCUMENTATION :
{extracted_doc}

LOG ANONYMISÉ À ANALYSER :
{anonymized_log}

RÉPONDS STRICTEMENT AU FORMAT JSON avec les clés :
- "explication": Explication de la cause racine en français.
- "solution": Procédure corrective étape par étape.
- "criticite": Niveau de gravité (Faible, Moyenne, Élevée, Critique).
- "source": Nom du constructeur ou de la doc.
"""
        response_text = query_gemini(prompt_cloud)

    try:
        if not response_text:
            raise Exception("Impossible d'obtenir une réponse des moteurs d'analyse.")

        cleaned_response = response_text
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3].strip()

        result_json = json.loads(cleaned_response)
        result_json["fichier_source"] = f"{source_file} via {engine_used}"
        
        if "Gemini Cloud" in engine_used:
            save_learned_log(raw_log, result_json)

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