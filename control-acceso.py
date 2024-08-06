import paho.mqtt.client as mqtt
import threading
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import datetime
import pytz
import LCD1602
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter, BaseCompositeFilter
pin_rojo = 17
pin_verde = 27
pin_azul = 22
# Configurar GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(pin_rojo, GPIO.OUT)
GPIO.setup(pin_verde, GPIO.OUT)
GPIO.setup(pin_azul, GPIO.OUT)

ejecutar_main = True

# Inicializar el evento
event = threading.Event()
#esperar_tecla_event = threading.Event()

# Obtener la fecha y hora actual en UTC
now_utc = datetime.datetime.utcnow()

# Definir la zona horaria local (por ejemplo, 'America/Argentina/Buenos_Aires' para Argentina)
local_timezone = pytz.timezone('America/Argentina/Buenos_Aires')

# Convertir la fecha y hora actual a la zona horaria local
now_local = now_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)

# Configuración del lector RFID
reader = SimpleMFRC522()

# Ruta al archivo de configuración descargado desde Firebase
cred = credentials.Certificate("credenciales-firebase.json")

# Inicializa la aplicación Firebase
firebase_admin.initialize_app(cred)

# Obtiene una instancia de la base de datos Firestore
db = firestore.client()

# Inicializar LCD
LCD1602.init(0x27, 1)
LCD1602.clear()

# Definir pines GPIO para filas y columnas del teclado matricial
pinFila = [21, 20, 16, 12]  # ROW1, ROW2, ROW3, ROW4
pinCol = [26, 19, 13]       # COL1, COL2, COL3

# Definir la disposición de las teclas en el teclado matricial
keys = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#']
]

# MQTT
TOPIC_ESTADO_PUBLISHER = "estado/publisher"
TOPIC_REGISTRAR = "web/registrar"
TOPIC_ELIMINAR = "web/eliminar"

def set_color(rojo, verde, azul):
    GPIO.output(pin_rojo, rojo)
    GPIO.output(pin_verde, verde)
    GPIO.output(pin_azul, azul)

pausar_main_event = threading.Event()
main_thread = None
main_thread_lock = threading.Lock()

def preguntar(arg):
    LCD1602.clear()
    LCD1602.write(0,0,"0->VOLVER A MENU")
    LCD1602.write(0,1,"1->REITENTAR")
    opcion = ""
    while not opcion:
        tecla = getKey()
        if tecla in ["0", "1"]:
            opcion = tecla

    if opcion == "0":
        event.set()
        main()
    elif opcion == "1":
        if arg == 1:
            registrar()
        elif arg == 2:
            eliminar()

def setup_matrix():
    # Configurar pines de fila como salida y pines de columna como entrada con pull-up
    for fila in pinFila:
        GPIO.setup(fila, GPIO.OUT)
        GPIO.output(fila, GPIO.HIGH)

    for columna in pinCol:
        GPIO.setup(columna, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Función para leer el teclado matricial y determinar qué tecla ha sido presionada
def getKey():
    
    k = None
    for c in range(len(pinCol)):
        for r in range(len(pinFila)):
            GPIO.output(pinFila[r], GPIO.LOW)
            if GPIO.input(pinCol[c]) == GPIO.LOW:
                time.sleep(0.05)  # Debounce de 20ms
                while GPIO.input(pinCol[c]) == GPIO.LOW:
                    pass
                k = keys[r][c]
            GPIO.output(pinFila[r], GPIO.HIGH)
    return k

def leer_tarjeta_rfid():
    try:
        id, _ = reader.read()
        return id
    except Exception as e:
        raise ValueError("Error al leer tarjeta RFID:", e)
        return None

def verificar_tarjeta_en_firebase(id_tarjeta):
    # Obtiene una referencia a la colección "Usuarios" en Firestore
    usuarios_ref = db.collection('usuarios')

    # Realiza una consulta para verificar si existe un usuario con el RFID proporcionado
    query = usuarios_ref.where(filter=FieldFilter('rfid', '==', id_tarjeta)).limit(1).get()

    # Comprueba si se encontró algún usuario con el RFID proporcionado
    if query:
        # El usuario con el RFID existe en la base de datos
        return True
    else:
        # No se encontró ningún usuario con el RFID proporcionado
        return False

def verificar_clave_en_firebase(clave):
    
    # Verificar que la clave coincida con la registrada en Firebase
    usuarios_ref = db.collection('usuarios')

    # Realiza una consulta para verificar si existe un usuario con el RFID proporcionado
    query = usuarios_ref.where(filter=FieldFilter('clave', '==', clave)).limit(1).get()

    # Comprueba si se encontró algún usuario con el RFID proporcionado
    if query:
        # El usuario con el RFID existe en la base de datos
        return True
    else:
        # No se encontró ningún usuario con el RFID proporcionado
        return False

# Función para ingresar clave numérica de 4 dígitos
def ingresar_clave():
    clave = ""
    contador = 0
    while len(clave) < 4:
        tecla = getKey()
        if tecla is not None and tecla.isdigit():
            clave += tecla
            LCD1602.write(contador,1,"*")  # Muestra "*" en lugar de la tecla presionada para ocultar la clave
            contador += 1
            time.sleep(0.5)  # Espera 0.5 segundos antes de limpiar la pantalla
    return clave

def registrar_evento(evento, **kwargs):
    id_tarjeta = kwargs.get('id_tarjeta')
    id_clave = kwargs.get('id_clave')
    
    #Validar que solo uno de los kwargs se reciban y no los dos
    if(id_tarjeta is None and id_clave is None) or (id_tarjeta is not None and id_clave is not None):
        raise ValueError("Debe proporcionar extactamente un argumento 'id_tarjeta' o 'id_clave'.")
    
    # Obtiene una referencia a la colección "Registros" en Firestore
    registros_ref = db.collection('registros')
    
    hora_fecha_local = datetime.datetime.now().strftime("%d-%m-%Y--%H:%M:%S")
    # Crea un nuevo documento para el registro de evento
    if id_tarjeta:
        nuevo_registro_ref = registros_ref.document(hora_fecha_local).set({
            'fecha_hora': now_local,
            'id_tarjeta': str(id_tarjeta),
            'evento': evento
        })
    if id_clave:
        nuevo_registro_ref = registros_ref.document(hora_fecha_local).set({
            'fecha_hora': now_local,
            'id_clave': str(id_clave),
            'evento': evento
        })
    time.sleep(0.5)
    main()
    
def ingresar_con_rfid(id_tarjeta):
    
    if id_tarjeta:
        if verificar_tarjeta_en_firebase(id_tarjeta):
            LCD1602.clear()
            LCD1602.write(0,0,"ACCESO PERMITIDO")
            registrar_evento("ingreso_rfid_exitoso", id_tarjeta=id_tarjeta)
            time.sleep(1)
            # Lógica para permitir el acceso al edificio
        else:
            LCD1602.clear()
            LCD1602.write(0,0,"ACCESO DENEGADO")
            registrar_evento("ingreso_rfid_fallido", id_tarjeta=id_tarjeta)
            time.sleep(1)
            # Lógica para denegar el acceso
    else:
        LCD1602.clear()
        LCD1602.write(0,0,"ERROR AL LEER")
        LCD1602.write(0,1,"RFID")
        
def ingresar_con_clave():
    LCD1602.clear()
    LCD1602.write(0,0,"INGRESE CLAVE:")
    clave = ingresar_clave()
    # Comprobar si se encontró algún usuario con la clave proporcionada
    if verificar_clave_en_firebase(clave):
        LCD1602.clear()
        LCD1602.write(0,0,"ACCESO PERMITIDO")
        registrar_evento("ingreso_clave_exitoso", id_clave=clave)
        time.sleep(1)
    else:
        LCD1602.clear()
        LCD1602.write(0,0,"ACCESO DENEGADO")
        registrar_evento("ingreso_clave_fallido", id_clave=clave)
        time.sleep(1)
    
def ingresar():
    LCD1602.clear()
    LCD1602.write(0,0,"1->RFID 2->CLAVE")
    LCD1602.write(4,1,"0->VOLVER")
    opcion = ""
    while not opcion:
        tecla = getKey()
        if tecla in ["1", "2", "0"]:
            opcion = tecla
    if opcion == "1":
        LCD1602.clear()
        LCD1602.write(0,0,"ACERQUE SU RFID")
        id_tarjeta = leer_tarjeta_rfid()
        ingresar_con_rfid(id_tarjeta)
    elif opcion == "2":
        ingresar_con_clave()
    elif opcion == "0":
        main()

def registrar():
    LCD1602.clear()
    LCD1602.write(4,0,"APROXIME")
    LCD1602.write(4,1,"TARJETA")
    id_tarjeta = leer_tarjeta_rfid()
    if id_tarjeta:
        if verificar_tarjeta_en_firebase(id_tarjeta):
            LCD1602.clear()
            LCD1602.write(2,0,"RFID YA ESTA")
            LCD1602.write(3,1,"REGISTRADO")
            registrar_evento("registro_denegado", id_tarjeta=id_tarjeta)
            time.sleep(1)
        else:
            LCD1602.clear()
            LCD1602.write(0,0,"CLAVE NUMERICA:")
            clave = ingresar_clave()

            # Obtener una referencia a la colección "Usuarios" en Firestore
            usuarios_ref = db.collection('usuarios')

            # Crear un nuevo documento para el usuario con los datos proporcionados
            nuevo_usuario_ref = usuarios_ref.document(str(id_tarjeta)).set({
                'rfid': id_tarjeta,
                'clave': clave
            })
            LCD1602.clear()
            LCD1602.write(4,0,"USUARIO")
            LCD1602.write(3,1,"REGISTRADO")
            registrar_evento("registro_exitoso", id_tarjeta=id_tarjeta)
            time.sleep(1)

def eliminar():
    LCD1602.clear()
    LCD1602.write(4,0,"APROXIME")
    LCD1602.write(4,1,"TARJETA")
    id_tarjeta = leer_tarjeta_rfid()
    if id_tarjeta:
        if verificar_tarjeta_en_firebase(id_tarjeta):
            LCD1602.clear()
            LCD1602.write(0,0,"CLAVE NUMERICA:")
            clave = ingresar_clave()
            
            # Verificar que la clave coincida con la registrada en Firestore
            usuarios_ref = db.collection('usuarios')
            query = usuarios_ref.where(filter= BaseCompositeFilter("AND",[FieldFilter('rfid', '==', id_tarjeta), FieldFilter('clave', '==', clave)])).limit(1).get()
            
            # Comprobar si se encontró algún usuario con la tarjeta y clave proporcionadas
            if query:
                # Eliminar el usuario de Firestore
                usuarios_ref.document(query[0].id).delete()
                LCD1602.clear()
                LCD1602.write(4,0,"USUARIO")
                LCD1602.write(3,1,"ELIMINADO")
                registrar_evento("eliminación_exitosa", id_tarjeta=id_tarjeta)
            else:
                LCD1602.clear()
                LCD1602.write(0,0,"CLAVE INCORRECTA")
                time.sleep(1)
                preguntar(2)
        else:
            LD1602.clear()
            LCD1602.write(0,0,"TARJETA NO ESTA")
            LCD1602.write(3,1,"REGISTRADA")
            time.sleep(1)
            preguntar(2)

# Definir las funciones de callback para MQTT
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    if msg.topic == "web/registrar":
        set_color(0,0,1)
        time.sleep(2)
        set_color(0,0,0)
    elif msg.topic == "web/eliminar":
        set_color(1,0,0)
        time.sleep(2)
        set_color(0,0,0)
    
def send_state_publisher(client):
    while True:
        client.publish(TOPIC_ESTADO_PUBLISHER, "1")
        time.sleep(30)

# Configurar cliente MQTT
def mqtt_loop():
    global client
    client = mqtt.Client()
    client.on_message = on_message

    client.connect("broker.emqx.io", 1883, 30)
    
    client.subscribe(TOPIC_REGISTRAR)
    client.subscribe(TOPIC_ELIMINAR)
    
    client.loop_start()
    return client

def start_main_thread():
    global main_thread
    pausar_main_event.set()  # Asegurarse de que el hilo principal esté en ejecución
    main_thread = threading.Thread(target=main)
    main_thread.start()

def main():
    global opcion
    opcion = None
    client = mqtt_loop()
      
    threading.Thread(target=send_state_publisher, args=(client,), daemon=True).start()
    
    LCD1602.clear()
    LCD1602.write(0, 0, "1->ING")
    LCD1602.write(0, 1, "2->REG")
    LCD1602.write(7, 1, "3->ELIM")
    while True:
        pausar_main_event.wait()
        opcion = None
        tecla = getKey()
        if tecla in ["1","2","3"]:
            opcion = tecla
        
        if opcion == "1":
            ingresar()
        elif opcion == "2":
            registrar()
        elif opcion == "3":
            eliminar()
try:
    set_color(0,0,0)
    setup_matrix()
    start_main_thread()
except KeyboardInterrupt:
    client.publish(TOPIC_ESTADO_PUBLISHER, "0")
except Exception as e:
    client.publish(TOPIC_ESTADO_PUBLISHER, "0")
