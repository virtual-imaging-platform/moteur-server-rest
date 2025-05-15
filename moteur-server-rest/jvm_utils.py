import jpype
import os
from config import get_env_variable

def load_classpath():
    """Load and return the classpath from moteur_home environment variable."""
    moteur_home = get_env_variable('MOTEUR_HOME')
    moteur_type = get_env_variable('MOTEUR_TYPE')
    
    classpath = f"{moteur_home}/{moteur_type}"
    for jar_file in filter(lambda x: x.endswith(".jar"), os.listdir(f"{moteur_home}/libs")):
        classpath += f":{os.path.join(moteur_home, 'libs', jar_file)}"
    for plugin_file in filter(lambda x: x.endswith(".jar"), os.listdir(f"{moteur_home}/plugins")):
        classpath += f":{os.path.join(moteur_home, 'plugins', plugin_file)}"
        
    return classpath
