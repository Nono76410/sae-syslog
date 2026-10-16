# LogAI — Diagnostic & Analyse de Logs Réseau

**LogAI** est un outil d'assistance au diagnostic et à l'analyse de logs réseau développé pour l'entreprise **Linkt**. L'application permet d'analyser des extraits de logs bruts pour en extraire la cause racine, proposer une solution corrective et fournir les références documentaires associées.

---

## 🚀 Fonctionnalités

* **Analyseur de Logs (Log Analyzer) :** Interface de copier-coller de logs bruts (Cisco, MikroTik, Fortinet, Teltonika, etc.).
* **Diagnostic assisté par IA :** Explication claire de la cause racine en français.
* **Résolution guidée :** Procédure pas à pas pour corriger le problème réseau.
* **Architecture RAG (Retrieval-Augmented Generation) :** Recherche sémantique locale dans la base documentaire via ChromaDB pour garantir des réponses fiables et sourcées.
* **Évolution future (Config Generator) :** Module de génération automatisée de configurations multi-constructeurs.

---

## 🛠️ Stack Technique

* **Langage :** Python 3.11+
* **Framework Web :** Flask
* **Base de données vectorielle :** ChromaDB
* **Moteur d'IA :** API Google Gemini (via prompt engineering & RAG)
* **Frontend :** HTML5, CSS3 (Bootstrap 5), JavaScript (Fetch API)

---

## 📂 Structure du Projet

```text
sae-syslog/
├── app.py                  # Application principale Flask et routes API
├── requirements.txt        # Dépendances Python du projet
├── .gitignore              # Exclusion des fichiers temporaires et virtuels
├── README.md               # Documentation du dépôt
├── knowledge_base/         # Fichiers de documentation constructeurs (RAG)
│   ├── cisco/
│   ├── fortinet/
│   └── mikrotik/
└── templates/
    └── index.html          # Interface utilisateur web
