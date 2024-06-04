import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import datetime
import pytz
from RPLCD.i2c import CharLCD
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import threading

# Configurar GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Obtener la fecha y hora actual en UTC
now_utc = datetime.datetime.utcnow()

# Definir la zona horaria local (por ejemplo, 'America/Argentina/Buenos_Aires' para Argentina)
local_timezone = pytz.timezone('America/Argentina/Buenos_Aires')

# Convertir la fecha y hora actual a la zona horaria local
now_local = now_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)

# Inicializar LCD
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8)
lcd.clear()

# Configuración del lector RFID
reader = SimpleMFRC522()

# Ruta al archivo de configuración descargado desde Firebase
cred = credentials.Certificate("credenciales-firebase.json")

# Inicializa la aplicación Firebase
firebase_admin.initialize_app(cred)

# Obtiene una instancia de la base de datos Firestore
db = firestore.client()

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

# Definición de las opciones
OPCION_INGRESAR = 1
OPCION_REGISTRAR = 2
OPCION_ELIMINAR = 3


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
                time.sleep(0.02)  # Debounce de 20ms
                while GPIO.input(pinCol[c]) == GPIO.LOW:
                    pass
                k = keys[r][c]
            GPIO.output(pinFila[r], GPIO.HIGH)
    return k

def mostrar_en_lcd(mensaje):
    lcd.clear()
    lcd.write_string(mensaje)

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
    while len(clave) < 4:
        tecla = getKey()
        if tecla is not None and tecla.isdigit():
            clave += tecla
            lcd.write_string("*")  # Muestra "*" en lugar de la tecla presionada para ocultar la clave
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
            lcd.clear()
            mostrar_en_lcd("ACCESO PERMITIDO")
            registrar_evento("ingreso_rfid_exitoso", id_tarjeta=id_tarjeta)
            # Lógica para permitir el acceso al edificio
        else:
            lcd.clear()
            mostrar_en_lcd("ACCESO DENEGADO")
            registrar_evento("ingreso_rfid_fallido", id_tarjeta=id_tarjeta)
            # Lógica para denegar el acceso
    else:
        lcd.clear()
        mostrar_en_lcd("ERROR AL LEER RFID")
        
def ingresar_con_clave():
    lcd.clear()
    mostrar_en_lcd(" INGRESE CLAVE\n\r NUMERICA:")
    clave = ingresar_clave()
    

    # Comprobar si se encontró algún usuario con la clave proporcionada
    if verificar_clave_en_firebase(clave):
        # La clave coincide con la de un usuario registrado
        lcd.clear()
        mostrar_en_lcd("ACCESO PERMITIDO")
        registrar_evento("ingreso_clave_exitoso", id_clave=clave)
    else:
        # La clave no coincide con ninguna clave registrada
        lcd.clear()
        mostrar_en_lcd("ACCESO DENEGADO")
        registrar_evento("ingreso_clave_fallido", id_clave=clave)
    
def ingresar():
    lcd.clear()
    mostrar_en_lcd("   1--->RFID\n\r   2--->CLAVE")
    
    opcion = ""
    while not opcion:
        tecla = getKey()
        if tecla in ["1", "2"]:
            opcion = tecla

    if opcion == "1":
        lcd.clear()
        mostrar_en_lcd("ACERQUE SU RFID")
        id_tarjeta = leer_tarjeta_rfid()
        ingresar_con_rfid(id_tarjeta)
    elif opcion == "2":
        ingresar_con_clave()

def registrar():
    lcd.clear()
    mostrar_en_lcd("APROXIME TARJETA")
    id_tarjeta = leer_tarjeta_rfid()
    if id_tarjeta:
        if verificar_tarjeta_en_firebase(id_tarjeta):
            lcd.clear()
            mostrar_en_lcd("RFID YA ESTA REGISTRADO")
            registrar_evento("registro_denegado", id_tarjeta=id_tarjeta)
        else:
            lcd.clear()
            mostrar_en_lcd("CLAVE NUMERICA:")
            clave = ingresar_clave()
            lcd.clear()
            mostrar_en_lcd("GUARDANDO...")

            # Obtener una referencia a la colección "Usuarios" en Firestore
            usuarios_ref = db.collection('usuarios')

            # Crear un nuevo documento para el usuario con los datos proporcionados
            nuevo_usuario_ref = usuarios_ref.document(str(id_tarjeta)).set({
                'rfid': id_tarjeta,
                'clave': clave
            })
            lcd.clear()
            mostrar_en_lcd("USUARIO REGISTRADO")
            registrar_evento("registro_exitoso", id_tarjeta=id_tarjeta)

def eliminar():
    lcd.clear()
    mostrar_en_lcd("APROXIME TARJETA")
    id_tarjeta = leer_tarjeta_rfid()
    if id_tarjeta:
        if verificar_tarjeta_en_firebase(id_tarjeta):
            lcd.clear()
            mostrar_en_lcd("CLAVE NUMERICA:")
            clave = ingresar_clave()

            # Verificar que la clave coincida con la registrada en Firestore
            usuarios_ref = db.collection('usuarios')
            query = usuarios_ref.where('rfid', '==', id_tarjeta).where('clave', '==', clave).limit(1).get()

            # Comprobar si se encontró algún usuario con la tarjeta y clave proporcionadas
            if query:
                # Eliminar el usuario de Firestore
                usuarios_ref.document(query[0].id).delete()
                lcd.clear()
                mostrar_en_lcd("USUARIO ELIMINADO")
                registrar_evento("eliminación_exitosa", id_tarjeta=id_tarjeta)
            else:
                # La clave no coincide con la registrada en Firestore
                lcd.clear()
                mostrar_en_lcd("CLAVE INCORRECTA")
        else:
            # La tarjeta no está registrada en Firestore
            lcd.clear()
            mostrar_en_lcd("TARJETA NO ESTA REGISTRADA")        
        
def cambiar_opcion(current_option, timer_runs):
    while timer_runs.is_set():
        lcd.clear()
        if current_option == OPCION_INGRESAR:
            lcd.clear()
            lcd.write_string("\t\t\t\tINGRESAR")
            lcd.cursor_pos = (1, 0)
            lcd.write_string("------->1<------")
            current_option = OPCION_REGISTRAR
        elif current_option == OPCION_REGISTRAR:
            lcd.clear()
            lcd.write_string("\t\t\t\tREGISTRAR")
            lcd.cursor_pos = (1, 0)
            lcd.write_string("------->2<------")
            current_option = OPCION_ELIMINAR
        elif current_option == OPCION_ELIMINAR:
            lcd.clear()
            lcd.write_string("\t\t\t\tELIMINAR")
            lcd.cursor_pos = (1, 0)
            lcd.write_string("------->3<------")
            current_option = OPCION_INGRESAR
        time.sleep(1)
def main():
    setup_matrix()
    lcd.clear()
    mostrar_en_lcd("\t\t\tBIENVENIDO")
    time.sleep(1)
    lcd.clear()
    
    # Lógica principal
    current_option = OPCION_INGRESAR
    timer_runs = threading.Event()
    timer_runs.set()
    # Inicia el temporizador en un hilo aparte
    timer = threading.Thread(target=cambiar_opcion, args=(current_option,timer_runs,))
    timer.start()
    
    while True:
        # Lógica para manejar la selección de opciones por parte del usuario
        opcion = ""
        while not opcion:
            tecla = getKey()
            if tecla in ["1", "2", "3"]:
                opcion = tecla
        timer_runs.clear()
        if opcion == "1":
            ingresar()
            
        elif opcion == "2":
            registrar()
        elif opcion == "3":
            eliminar()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
