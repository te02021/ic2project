import { initializeFirebase, createUserWithEmailAndPassword, setDoc, doc, getUserByUsername } from './firebase.js';
import config from './config.js';

window.addEventListener('DOMContentLoaded', () => {
    const isLoggedIn = localStorage.getItem('loggedIn');
    if (isLoggedIn) {
        // Si el usuario ya ha iniciado sesión, redirigir a admin.html
        window.location.href = 'admin.html';
    }
});

initializeFirebase().then(({ auth, db }) => {
    const SECRET_KEY = config.SECRET_KEY

    function encrypt_data(string) {
        string = unescape(encodeURIComponent(string));
        var newString = '', char, nextChar, combinedCharCode;
        for (var i = 0; i < string.length; i += 2) {
            char = string.charCodeAt(i);

            if ((i + 1) < string.length) {


                nextChar = string.charCodeAt(i + 1) - 31;


                combinedCharCode = char + "" + nextChar.toLocaleString('en', {
                    minimumIntegerDigits: 2
                });

                newString += String.fromCharCode(parseInt(combinedCharCode, 10));

            } else {


                newString += string.charAt(i);
            }
        }
      return newString.split("").reduce((hex,c)=>hex+=c.charCodeAt(0).toString(16).padStart(4,"0"),"");
    }

    function decrypt_data(string) {

        var newString = '', char, codeStr, firstCharCode, lastCharCode;
        string = string.match(/.{1,4}/g).reduce((acc,char)=>acc+String.fromCharCode(parseInt(char, 16)),"");
        for (var i = 0; i < string.length; i++) {
            char = string.charCodeAt(i);
            if (char > 132) {
                codeStr = char.toString(10);
    
                firstCharCode = parseInt(codeStr.substring(0, codeStr.length - 2), 10);
    
                lastCharCode = parseInt(codeStr.substring(codeStr.length - 2, codeStr.length), 10) + 31;
    
                newString += String.fromCharCode(firstCharCode) + String.fromCharCode(lastCharCode);
            } else {
                newString += string.charAt(i);
            }
        }
        return newString;
    }

    //Manejar el evento de envío del formulario de login
    document.getElementById('loginForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const button = document.getElementById('loginButton');
        var username = document.getElementById("usernameLogin");
        var password = document.getElementById("passwordLogin");

        button.disabled = true; // Deshabilitar el botón para prevenir múltiples clics
        // Guardar el texto original del botón
        const originalText = button.innerHTML;
        // Reemplazar el contenido del botón con el loader
        button.innerHTML = '<div class="loader"></div>';
        getUserByUsername(db, username.value)
            .then((userData) => {
                if (userData) {
                    // Descifrar la contraseña almacenada en Firebase
                    var decryptedPassword = decrypt_data(userData.encryptedPassword);
                    console.log(decryptedPassword)
                    // Comparar la contraseña descifrada con la contraseña ingresada por el usuario
                    if (password.value === decryptedPassword) {
                        // Después de un inicio de sesión exitoso
                        localStorage.setItem('loggedIn', 'true');
                        button.innerHTML = originalText;
                        button.disabled = false;
                        // Redirigir a la página de administrador
                        window.location.href = "admin.html";
                        
                        // Limpiar los campos de entrada después de iniciar sesión exitosamente
                        username.value = '';
                        password.value = '';
                    } else {
                        alert("Contraseña incorrecta");
                        username.value = '';
                        password.value = '';
                        button.innerHTML = originalText;
                        button.disabled = false;
                    }
                } else {
                    alert("Usuario no encontrado");
                    username.value = '';
                    password.value = '';
                    button.innerHTML = originalText;
                    button.disabled = false;
                }
            })
            .catch((error) => {
                alert("Error al iniciar sesión: " + error.message);
                username.value = '';
                password.value = '';
                button.innerHTML = originalText;
                button.disabled = false;
            });
    });
  
    // Manejar el evento de envío del formulario de registro
    document.getElementById('registerForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const button = document.getElementById('registerButton');
        var username = document.getElementById("usernameRegister");
        var email = document.getElementById("emailRegister");
        var password = document.getElementById("passwordRegister");
        var passwordCheck = document.getElementById("passwordRegisterCheck");
        var encryptedPassword = encrypt_data(password.value);

        button.disabled = true; // Deshabilitar el botón para prevenir múltiples clics
        const originalText = button.innerHTML;
        // Reemplazar el contenido del botón con el loader
        button.innerHTML = '<div class="loader"></div>';

        createUserWithEmailAndPassword(auth, email.value, encryptedPassword)
            .then((userCredential) => {
                var user = userCredential.user;
                setDoc(doc(db, "usuarios", user.uid), {
                    username: username.value,
                    password: password.value,
                    encryptedPassword: encryptedPassword
                })
                .then(() => {
                    alert("Registro exitoso: " + username.value);
                    username.value = '';
                    email.value = '';
                    password.value= '';
                    passwordCheck.value = '';
                    button.innerHTML = originalText;
                    button.disabled = false;
                })
                .catch((error) => {
                    alert("Error al guardar en Firestore: " + error.message);
                    username.value = '';
                    email.value = '';
                    password.value= '';
                    passwordCheck.value = '';
                    button.innerHTML = originalText;
                    button.disabled = false;
                });
            })
            .catch((error) => {
                var errorMessage = error.message;
                alert("Error: " + errorMessage);
                username.value = '';
                email.value = '';
                password.value= '';
                passwordCheck.value = '';
                button.innerHTML = originalText;
                button.disabled = false;
            });
    });
});

$(document).on('click', '.message a', function(){
    $('form').animate({height: "toggle", opacity: "toggle"}, "slow");
    document.getElementById("usernameRegister").value = '';
    document.getElementById("emailRegister").value = '';
    document.getElementById("passwordRegister").value = '';
    document.getElementById("passwordRegisterCheck").value = '';
    document.getElementById("usernameLogin").value = '';
    document.getElementById("passwordLogin").value = '';
});


