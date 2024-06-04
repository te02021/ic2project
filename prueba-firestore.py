import firebase_admin
from firebase_admin import credentials, firestore

# Ruta al archivo de configuración descargado desde Firebase
cred = credentials.Certificate("credenciales-firebase.json")

# Inicializa la aplicación Firebase
firebase_admin.initialize_app(cred)

# Obtiene una instancia de la base de datos Firestore
db = firestore.client()

# Función para agregar un usuario a la colección 'usuarios'
def agregar_usuario():
    # Solicitar entrada de datos al usuario
    id_usuario = input("Ingrese el ID del usuario: ")
    rfid = input("Ingrese el RFID del usuario: ")
    clave = input("Ingrese la clave del usuario: ")
    
    # Referencia a la colección 'usuarios'
    usuarios_ref = db.collection('usuarios')
    
    # Documento que representa el usuario
    usuario_data = {
        'id_usuario': id_usuario,
        'rfid': rfid,
        'clave': clave
    }
    
    # Agregar el usuario a la colección
    usuarios_ref.document(id_usuario).set(usuario_data)

# Función para agregar un registro a la colección 'registros'
def agregar_registro():
    # Solicitar entrada de datos al usuario
    fecha_hora = input("Ingrese la fecha y hora del registro (YYYY-MM-DD HH:MM:SS): ")
    id_usuario = input("Ingrese el ID del usuario: ")
    evento = input("Ingrese el evento: ")
    
    # Referencia a la colección 'registros'
    registros_ref = db.collection('registros')
    
    # Documento que representa el registro
    registro_data = {
        'fecha_hora': fecha_hora,
        'id_usuario': id_usuario,
        'evento': evento
    }
    
    # Agregar el registro a la colección
    registros_ref.add(registro_data)

# Solicitar al usuario qué acción realizar
accion = input("¿Qué acción deseas realizar? (1 para agregar usuario, 2 para agregar registro): ")

# Ejecutar la acción correspondiente
if accion == '1':
    agregar_usuario()
elif accion == '2':
    agregar_registro()
else:
    print("Acción no válida.")