//import 'https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.3/mqttws31.min.js';
window.addEventListener('DOMContentLoaded', () => {
    // Obtener estado del publisher HTML y cambiarlo en base al publisher python

    const publisherState = document.getElementById('publisherState')
    const registerUser = document.getElementById('registerUser');
    const deleteUser = document.getElementById('deleteUser');
    // const toggleStateButton = document.getElementById('toggleStateButton');
    const isLoggedIn = localStorage.getItem('loggedIn');  

    var client = new Paho.MQTT.Client("broker.emqx.io", 8083, "web-client");

    const statePublisherTimeout = 35000; // 30 segundos
    let lastStatePublisherTime = 0;
    let statePublisherTimer = null;


    // Función para actualizar el estado de los elementos <li> en base al estado del sistema
    function updateUserActionsState() {
        if (publisherState.classList.contains('redState')) {
            registerUser.classList.add('disabled');
            deleteUser.classList.add('disabled');
        } else {
            registerUser.classList.remove('disabled');
            deleteUser.classList.remove('disabled');
        }
    } 

    // Función para iniciar el temporizador
    function startStatePublisherTimer() {
        statePublisherTimer = setTimeout(handleStatePublisherTimeout, statePublisherTimeout);
    }

    // Función para reiniciar el temporizador
    function resetStatePublisherTimer() {
        clearTimeout(statePublisherTimer);
        startStatePublisherTimer();
    }

    // Función para manejar el tiempo de espera del keep-alive
    function handleStatePublisherTimeout() {
        // Obtener el tiempo actual
        const currentTime = new Date().getTime();

        // Calcular la diferencia de tiempo desde la última actualización del estado del publicador
        const elapsedTime = currentTime - lastStatePublisherTime;

        // Comprobar si ha pasado más de 30 segundos desde la última actualización
        if (elapsedTime > statePublisherTimeout) {
            // Realizar acciones cuando se supere el tiempo de espera
            console.log("El publicador no está en funcionamiento. Tomando medidas adicionales...");
            publisherState.classList.remove('greenState');
            publisherState.classList.add('redState');
            updateUserActionsState()
        }
    }

    client.onConnectionLost = onConnectionLost;
    client.onMessageArrived = onMessageArrived;
    client.connect({
        onSuccess: onConnect,
        useSSL: false
    });

  
    function onConnect() {
        client.subscribe("estado/publisher");
        client.subscribe("funcion/registrar");
        client.subscribe("funcion/eliminar");
        startStatePublisherTimer()
    }
  
    function onConnectionLost(responseObject) {
        if (responseObject.errorCode !== 0) {
            console.log("Conexión perdida: " + responseObject.errorMessage);
        }
    }
  
    function onMessageArrived(message) {
        // Realizar acciones según el tópico
        if (message.destinationName === "estado/publisher") {
            if (message.payloadString === '1') {
                publisherState.classList.remove('redState');
                publisherState.classList.add('greenState');
            } else {
                publisherState.classList.remove('greenState');
                publisherState.classList.add('redState');
            }
            resetStatePublisherTimer()
            updateUserActionsState()
            // Procesar mensaje de estado/publisher
            console.log(`Estado publisher: ${message.payloadString}`);
        } else if (message.destinationName === "funcion/registrar") {
            // Procesar mensaje de funcion/registrar
            console.log(`Función registrar: ${message.payloadString}`);
        } else if (message.destinationName === "funcion/eliminar") {
            // Procesar mensaje de funcion/eliminar
            console.log(`Función eliminar: ${message.payloadString}`);
        }
    
    }

    // Función para enviar un mensaje al publisher
    function sendMessage(topic, message) {
        var message = new Paho.MQTT.Message(message);
        message.destinationName = topic;
        client.send(message);
    }

    
    if (!isLoggedIn) {
        // Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        alert("Debes iniciar sesion")
        window.location.href = 'index.html';
    }   else {
        // Mostrar el contenido de la página de administrador
        document.body.style.display = 'flex';
    }

    

    // Funcionalidad registrar usuario
    registerUser.addEventListener('click', () =>{
        if (registerUser.classList.contains('disabled')) {
            alert("El sistema se encuentra fuera de funcionamiento")
        } else {
            sendMessage("web/registrar", "1");
            alert("Dirijase al sistema fisico para continuar con el registro")
        }
    })
    
    // Funcionalidad eliminar usuario
    deleteUser.addEventListener('click', ()=>{
        if (deleteUser.classList.contains('disabled')) {
            alert("El sistema se encuentra fuera de funcionamiento")
        } else {
            sendMessage("web/eliminar", "1");
            alert("Dirijase al sistema fisico para continuar con la eliminacion")
        }
    })

    

    // Bloquear retroceso en el navegador
    window.addEventListener('popstate', function(event) {
        const isLoggedIn = localStorage.getItem('loggedIn');
        if (isLoggedIn) {
            // Si el usuario está autenticado, bloquear el retroceso
            history.pushState(null, '', location.href);
            //alert('No puedes salir de la página de administrador mientras estás autenticado.');
        }
    });

    // Añadir un estado al historial para controlar el evento de retroceso
    history.pushState(null, '', location.href);
    updateUserActionsState();
});

// Event listener para el botón de cerrar sesión
document.getElementById('logoutButton').addEventListener('click', function() {
    localStorage.removeItem('loggedIn');
    // Redirigir a la página de inicio (index.html)
    window.location.href = "index.html";
});

