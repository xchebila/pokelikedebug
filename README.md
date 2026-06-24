# Pokelike Debugger

Application de debug pour [Pokelike](https://pokelike.xyz) — modifier l'équipe, les Pokédollars, forcer des rencontres et bien plus.

Compatible avec **tous les navigateurs** via un script Tampermonkey.

---

## Installation (testeurs)

### 1. Télécharger l'application

- **Windows** : télécharger `PokelikeDebugger.exe` et le lancer directement (aucune installation requise)
- **Mac** : télécharger `PokelikeDebugger.app`, le dézipper et l'ouvrir

> Sur Mac, si macOS bloque l'ouverture : clic droit → **Ouvrir** → Ouvrir quand même.

---

### 2. Configuration initiale (première ouverture uniquement)

Au premier lancement, une fenêtre de configuration apparaît automatiquement.

#### Étape 1 — Installer Tampermonkey

Tampermonkey est une extension de navigateur qui permet d'exécuter des scripts sur les pages web.
Installez-le pour votre navigateur :

| Navigateur | Lien |
|-----------|------|
| Chrome    | [Chrome Web Store](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo) |
| Firefox   | [Firefox Add-ons](https://addons.mozilla.org/firefox/addon/tampermonkey/) |
| Edge      | [Edge Add-ons](https://microsoftedge.microsoft.com/addons/detail/tampermonkey/iikmkjmpaadaobahmlepeloendndfphd) |
| Opera     | [Opera Add-ons](https://addons.opera.com/extensions/details/tampermonkey-beta/) |

> Si Tampermonkey est déjà installé, passez directement à l'étape 2.

#### Étape 2 — Installer le script

Dans la fenêtre de configuration, cliquez sur **"Installer le script Tampermonkey"**.

L'app ouvre une page dans votre navigateur par défaut. Tampermonkey affiche une page d'installation — cliquez sur **"Installer"**.

> **Si la page d'installation ne s'affiche pas automatiquement :**
> Un lien `http://127.0.0.1:...` s'affiche dans la fenêtre de configuration.
> Copiez-le et collez-le dans la barre d'adresse du navigateur où Tampermonkey est installé.
> Tampermonkey intercepte les URLs se terminant par `.user.js` et propose l'installation.

#### Étape 3 — Autoriser les scripts dans Tampermonkey

Sur certains navigateurs (Arc, Chrome récent), les userscripts sont désactivés par défaut.
Si le badge **"🔌"** n'apparaît pas en bas à droite du jeu après l'étape 2 :

1. Ouvrez Tampermonkey → **Tableau de bord** → **Paramètres**
2. Passez le niveau de sécurité sur **"Détendu"** ou activez les scripts utilisateur dans les paramètres avancés

Voir l'[aide officielle Tampermonkey](https://www.tampermonkey.net/faq.php?q=Q209#Q209) pour les instructions détaillées selon votre navigateur.

#### Étape 4 — C'est parti

Cliquez sur **"C'est fait, démarrer l'app →"** dans la fenêtre de configuration.

---

### 3. Utilisation au quotidien

1. Lancer **Pokelike Debugger**
2. Ouvrir votre navigateur et aller sur **[pokelike.xyz](https://pokelike.xyz)**
3. L'app affiche **"Connecté"** dès que la connexion est établie

Le script se reconnecte automatiquement si la page est rechargée.

---

## Fonctionnalités

| Onglet | Description |
|--------|-------------|
| **Contrôles → ✨ Force Shiny** | Active le shiny garanti pour la prochaine rencontre ou le starter |
| **Contrôles → Équipe** | Affiche l'équipe en temps réel (PV, niveau, shiny…) |
| **Contrôles → Pokédollars** | Affiche et modifie le solde |
| **Pokédex** | Affiche les Pokémon vus/capturés |
| **Hall of Fame** | Historique des parties terminées |
| **Rencontre** | Force le Pokémon de la prochaine rencontre sauvage |

---

## Dépannage

**L'app affiche "Déconnecté" en permanence**
- Vérifiez que Tampermonkey est bien installé et actif
- Vérifiez que le script "Pokelike Debugger Bridge" est activé dans Tampermonkey (icône → liste des scripts)
- Rechargez la page pokelike.xyz

**Le script ne s'est pas installé automatiquement**
- Vérifiez que Tampermonkey est installé dans le bon navigateur
- Réouvrez la configuration : supprimez le fichier `~/.pokelike-debugger/setup_done` et relancez l'app

**Sur Mac : "L'app ne peut pas être ouverte car elle provient d'un développeur non identifié"**
- Clic droit sur l'app → **Ouvrir** → **Ouvrir quand même**

---

## Pour les développeurs

```bash
# Créer un environnement virtuel et installer les dépendances
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate.bat       # Windows

pip install -r requirements.txt

# Lancer sans builder
python main.py

# Builder
# Mac :
pyinstaller PokelikeDebugger.spec
# Windows :
build_windows.bat
```
