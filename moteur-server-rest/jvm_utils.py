import jpype
import os
from config import get_env_variable

def start_jvm():
    """Start the JVM if it isn't already started."""
    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=[get_env_variable("MARIADB_JAR_PATH")])

def shutdown_jvm():
    """Shutdown the JVM if it is currently running."""
    if jpype.isJVMStarted():
        jpype.shutdownJVM()

def load_classpath():
    """Load and return the classpath from MOTEUR_HOME environment variable."""
    moteur_home = get_env_variable('MOTEUR_HOME')
    
    classpath = f"{moteur_home}/moteurlite.jar"
    for jar_file in filter(lambda x: x.endswith(".jar"), os.listdir(f"{moteur_home}/libs")):
        classpath += f":{os.path.join(moteur_home, 'libs', jar_file)}"
    for plugin_file in filter(lambda x: x.endswith(".jar"), os.listdir(f"{moteur_home}/plugins")):
        classpath += f":{os.path.join(moteur_home, 'plugins', plugin_file)}"
        
    return classpath
