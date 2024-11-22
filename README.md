# moteur-server-rest

Nouvelle version de moteur serveur. Utilisation du protocole REST et de la librairie Flask pour Python.

## Configuration

Tout d'abord, il faut créer un fichier `.env` à la racine du projet suivant la structure du fichier `.env.template`. Ce fichier contiendra les variables d'environnement nécessaires au bon fonctionnement du serveur.
Il faut ensuite mettre à jour le fichier de configuration `/vip/.vip/vip.conf` en fonction de l'utilisateur qui va lancer le serveur et de la configuration du fichier `.env`.
Pour le fichier `vip.conf`, il faut mettre à jour les variables `workflows.directory` et `datamanager.users.home` ainsi que `datamanager.groups.home` pour refléter les chemins réels des répertoires sur votre système.
Il est possible d'utiliser les fichiers `.env.apache` et `.env.vip` pour configurer les variables d'environnement pour Apache et VIP, à condition de les renommer en `.env` avant de lancer le serveur.

## Lancer le serveur

Pour lancer le serveur en mode développement, vous devez avoir Poetry installé sur votre machine. Ensuite, il suffit de lancer la commande suivante dans le répertoire du projet moteur-server-rest:

```bash
poetry install
poetry run python index.py
```

Pour lancer le serveur en mode production, il faudra utiliser nohup en plus de la commande précédente:

```bash
nohup poetry run python index.py > app.log 2>&1 &
```