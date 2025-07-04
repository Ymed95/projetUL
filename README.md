🚩 Projet fil rouge DevOps – Mise en Usine Logiciel

1. Arborescence du projet
.github/workflows/ :
Contient les workflows GitHub Actions pour l’automatisation CI/CD (déploiement, tests, qualité, etc.).
→ Permet de déclencher automatiquement chaque étape du pipeline à chaque push ou PR.

app/ :
Code source principal de l’application Python (API, logique métier, endpoints REST, etc.).

infrastructure/ :
Scripts Terraform (provisionnement Azure) et playbooks Ansible (configuration VM, installation Docker, déploiement applicatif).

monitoring/ :
Configurations Prometheus, Grafana, pour la supervision, la collecte des métriques et des logs.

tests/ :
Scripts de tests unitaires et d’intégration Python.
→ Garantit la qualité et la non-régression du code avant tout déploiement.

.env :
Variables d’environnement externalisées pour l’application.
→ Sépare la config du code, facilite la maintenance et la sécurité.

.flake8 :
Configuration du linter Python pour appliquer les standards de qualité de code (PEP8).

Dockerfile, docker-compose.yml, Dockerfile.test :
Conteneurisation de l’application et orchestration multi-conteneurs (web, API, monitoring).
→ Facilite le déploiement, l’isolation et la portabilité.

requirements.txt :
Dépendances Python (Flask, pytest, requests, etc.).

sonar-project.properties :
Configuration SonarQube pour l’analyse statique du code Python.

2. Détail des contraintes techniques et des choix
✅ Repository GitHub avec Git Flow
Pourquoi ?
Pour assurer un historique propre, faciliter les revues, permettre un développement collaboratif organisé (branches main, feature/*, develop).

✅ Travail collaboratif / équitablement réparti
Pourquoi ?
Chacun a un rôle : dev app, tests, infra, CI/CD, monitoring.
→ Tout est versionné dans le même repo, ce qui garantit la traçabilité.

✅ Pipeline CI/CD avec tests automatisés
Comment ?

Workflow .github/workflows/deployment.yml :

Job Terraform : Provisionne l’infra Azure.

Job Ansible : Configure la VM, installe Docker, déploie les conteneurs.

Job de tests :

Avant tout déploiement, lance les tests unitaires et d’intégration (dossier tests/) avec pytest.

Qualité Python :

flake8 vérifie le respect des standards PEP8.

coverage mesure la couverture des tests.

Bloc typique :

text
- name: Install dependencies and run tests
  run: |
    pip install -r requirements.txt
    pip install pytest flake8 coverage
    flake8 app/
    pytest --cov=app tests/
Pourquoi ?
Pour garantir que seul du code testé, propre et fonctionnel est déployé.

✅ Analyse de qualité de code (SonarQube)
Comment ?

sonar-project.properties configure SonarQube pour l’analyse statique.

Peut être intégré au pipeline pour bloquer les merges si la qualité n’est pas suffisante.

Pourquoi ?
Pour détecter les bugs, duplications, failles potentielles avant la mise en production.

✅ Monitoring avec Prometheus/Promtail/Grafana
Comment ?

Prometheus collecte les métriques de l’application et du système.

Promtail collecte les logs applicatifs, envoyés à Grafana Loki.

Grafana permet de visualiser en temps réel la santé et la performance de l’app.

Pourquoi ?
Pour anticiper les incidents, détecter les anomalies et assurer la disponibilité.

✅ Déploiement IaC (Terraform + Ansible)
Comment ?

Terraform (dans infrastructure/) :

Provisionne la VM, le réseau, l’IP publique, le NSG (ports 22, 80, 443, 3000, 5000, 9090).

Injection de la clé publique SSH :

text
admin_ssh_key {
  username   = var.vm_admin_username
  public_key = file(var.ssh_public_key_path)
}
Règles NSG pour autoriser l’accès aux services et à l’admin.

Ansible :

Installe Docker, déploie les conteneurs, configure le système.

Sécurité :

Clé publique SSH injectée dans la VM via Terraform.

Clé privée SSH stockée dans les secrets GitHub, jamais dans le repo.

Chargement sécurisé via webfactory/ssh-agent dans le workflow.

Pourquoi ?
Pour garantir la reproductibilité, la sécurité et l’automatisation complète de l’infra.

✅ Connexion sécurisée à Azure avec OIDC et App Registration
Comment ?

App Registration dans Azure AD, avec “justificatif fédéré” (federated credential) pour autoriser GitHub Actions via OIDC.

Rôle Contributor donné à l’App Registration sur la souscription Azure.

Secrets GitHub :

AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID (pas de secret client !)

Pourquoi ?

Authentification moderne, sécurisée, sans secrets statiques.

Respect des meilleures pratiques cloud.

✅ Déploiement automatisé sur VM Azure
Comment ?

Provisionnement de l’infra et récupération dynamique de l’IP publique (avec attente/refresh pour éviter les soucis de propagation Azure).

Transmission de l’IP à Ansible pour la configuration.

Génération dynamique de l’inventaire avec l’utilisateur SSH correct (azureuser).

Pourquoi ?
Pour garantir que la configuration applicative se fait sur la bonne VM, avec la bonne clé, et sans intervention manuelle.

✅ Tests unitaires et d’intégration
Comment ?

Dossier tests/ :

Scripts de tests Python exécutés avec pytest et coverage.

Lancement automatique dans le pipeline.

Pourquoi ?
Pour garantir la qualité, la non-régression et la robustesse du code.

✅ Containerisation (Docker)
Comment ?

Dockerfile : Définit l’image de l’application.

docker-compose.yml : Orchestration multi-conteneurs (web, API, monitoring, etc.).

Dockerfile.test : Pour exécuter les tests dans un environnement isolé.

Healthchecks intégrés pour surveiller l’état des conteneurs.

Pourquoi ?
Pour l’isolation, la portabilité, la cohérence entre dev, test et prod, et la facilité de déploiement.

✅ Configuration externalisée
Comment ?

Fichier .env : Centralise les variables d’environnement (ports, secrets, URLs, etc.).

Monté dans les conteneurs Docker.

Pourquoi ?
Pour séparer la configuration du code, faciliter la maintenance et la sécurité.

✅ Logs structurés
Comment ?

Application et monitoring configurés pour produire des logs lisibles, exploitables par Promtail et Grafana.

Pourquoi ?
Pour faciliter le debug, le suivi et l’observabilité.

🛠️ Pourquoi chaque choix ? (Synthèse)
Terraform : Reproductibilité, gestion déclarative, versionnement de l’infra.

Ansible : Automatisation de la configuration, déploiement applicatif, zéro SSH manuel.

GitHub Actions : Automatisation, sécurité (gestion des secrets, OIDC), traçabilité.

Docker : Isolation, portabilité, cohérence dev/test/prod.

Sécurité SSH : Jamais de clé privée dans le repo, usage de l’agent SSH.

NSG Azure : Ports ouverts explicitement, principe du moindre privilège.

OIDC : Authentification moderne, sécurisée, sans secrets statiques.

Prometheus/Grafana : Monitoring temps réel, alerting, observabilité.

Tests et qualité Python : pytest, flake8, coverage, SonarQube pour garantir un code robuste et maintenable.

🚦 Diagnostic et résolutions de problèmes rencontrés
Accès SSH : Synchronisation stricte des clés, utilisateur correct, agent SSH.

Propagation IP Azure : Step terraform apply -refresh-only, boucle d’attente.

Conteneurs “unhealthy” : Diagnostic via docker logs, correction des permissions .env.

Accès réseau : Vérification/ouverture des ports NSG et firewall local.

Tests/Qualité : Blocage du déploiement si les tests ou le lint Python échouent.

📑 Conclusion
Ce projet illustre la mise en place professionnelle d’une chaîne DevOps complète :

Infra as Code (Terraform)

Déploiement automatisé (GitHub Actions + OIDC)

Configuration système (Ansible)

Containerisation et monitoring (Docker, Prometheus, Grafana)

Qualité et sécurité (tests, lint, SonarQube, gestion des secrets, NSG, OIDC)
