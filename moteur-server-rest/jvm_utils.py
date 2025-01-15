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
    """Load and return the classpath from app_location environment variable."""
    app_location = get_env_variable('APP_LOCATION')
    
    classpath = f"{app_location}/moteurlite.jar"
    for jar_file in filter(lambda x: x.endswith(".jar"), os.listdir(f"{app_location}/libs")):
        classpath += f":{os.path.join(app_location, 'libs', jar_file)}"
    for plugin_file in filter(lambda x: x.endswith(".jar"), os.listdir(f"{app_location}/plugins")):
        classpath += f":{os.path.join(app_location, 'plugins', plugin_file)}"
        
    return classpath
