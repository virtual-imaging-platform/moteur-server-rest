# moteur-server-rest

Nouvelle version de moteur serveur. Utilisation du protocole REST et de la librairie Flask pour Python.

## Configuration

Tout d'abord, il faut créer un fichier `.env` à la racine du projet suivant la structure du fichier `.env.template`. Ce fichier contiendra les variables d'environnement nécessaires au bon fonctionnement du serveur.

Il faut ensuite mettre à jour le fichier de configuration `/vip/.vip/vip.conf` en fonction de l'utilisateur qui va lancer le serveur et de la configuration du fichier `.env`.
Pour le fichier `vip.conf`, il faut mettre à jour les variables `workflows.directory` et `datamanager.users.home` ainsi que `datamanager.groups.home` pour refléter les chemins réels des répertoires sur votre système.

Il est possible d'utiliser les fichiers `.env.apache` et `.env.vip` pour configurer les variables d'environnement pour Apache et VIP, à condition de les renommer en `.env` avant de lancer le serveur.

Enfin, il est nécessaire de télécharger le fichier .jar permettant de se connecter à la base de données mariadb et de le placer dans le répertoire indiqué par la variable d'environnement `MARIADB_JAR_PATH` du fichier `.env`. Le fichier est disponible à l'adresse suivante: https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/1.1.10/mariadb-java-client-1.1.10.jar.

## Lancer le serveur

### Développement (uv)
Dans le répertoire du projet `moteur-server-rest`:

```bash
uv sync
uv run moteur-server-rest/server.py
```

### Production (Gunicorn via uv)
Depuis le dossier parent contenant les fichiers de conf (par ex. `/vip/moteur-server`), sans changer de répertoire:

```bash
uv run gunicorn -w 2 -b 0.0.0.0:5000 --pythonpath moteur-server-rest wsgi:app
```

### Service systemd (exemple)
Fichier d'unité, par ex. `/etc/systemd/system/moteur-server.service`:

```ini
[Unit]
Description=Moteur-server Service
After=syslog.target network.target

[Service]
Type=simple
WorkingDirectory=/vip/moteur-server
ExecStart=/vip/.local/bin/uv run gunicorn -w 2 -b 0.0.0.0:5000 --pythonpath moteur-server-rest wsgi:app
SuccessExitStatus=143
Environment="PATH=/vip/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="X509_USER_PROXY=/workflows/x509up_server"
User=vip
Group=vip
Restart=on-failure
RestartSec=3
KillMode=process

[Install]
WantedBy=multi-user.target
```

Puis:

```bash
sudo systemctl restart msr
sudo systemctl daemon-reload
```