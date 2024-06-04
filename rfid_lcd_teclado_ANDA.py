import RPi.GPIO as GPIO
import time
from mfrc522 import SimpleMFRC522
from RPLCD.i2c import CharLCD

# Inicializar lector RFID
reader = SimpleMFRC522()

# Inicializar LCD
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8)
lcd.clear()

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

# Configurar GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

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

# Mostrar opciones en el LCD
def mostrar_opciones():
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("1. Apoye tarjeta")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("2. Ingrese clave")

# Solicitar clave en el LCD
def solicitar_clave():
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("Ingrese clave:")
    lcd.cursor_pos = (1, 0)

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

try:
    while True:
        mostrar_opciones()
        while True:
            opcion = getKey()  # Lee la opción seleccionada
            if opcion == '1':
                print("Opción 1 seleccionada: Apoye tarjeta en lector")
                lcd.clear()
                lcd.write_string("Apoye tarjeta...")
                id, _ = reader.read()  # Leer el ID de la tarjeta
                print("ID de tarjeta leído:", id)
                time.sleep(2)  # Espera 2 segundos antes de volver al menú principal
                break
            elif opcion == '2':
                print("Opción 2 seleccionada: Ingrese clave numérica de 4 dígitos")
                solicitar_clave()
                clave = ingresar_clave()  # Solicitar clave al usuario
                print("Clave ingresada:", clave)  # Muestra la clave ingresada en la consola
                time.sleep(2)  # Espera 2 segundos antes de volver al menú principal
                break
            else:
                print("Opción inválida")
                time.sleep(2)  # Espera 2 segundos antes de volver al menú principal

except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()  # Limpia los pines GPIO al finalizar
