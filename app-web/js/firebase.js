import { initializeApp } from "https://www.gstatic.com/firebasejs/9.0.0/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/9.0.0/firebase-auth.js";
import { getFirestore, setDoc, doc, collection, query, where, limit, getDocs } from "https://www.gstatic.com/firebasejs/9.0.0/firebase-firestore.js";

function getFirebaseConfig() {
    return fetch('firebaseConfig.json')
        .then(response => response.json());
}
  
function initializeFirebase() {
    return getFirebaseConfig()
        .then(firebaseConfig => {
            // Inicializar Firebase
            const app = initializeApp(firebaseConfig);
            const auth = getAuth();
            const db = getFirestore(app);

            // Retornar auth y db para su uso en otros archivos
            return { auth, db };
        });
}

// Función para obtener los datos del usuario por su nombre de usuario
function getUserByUsername(db, username) {
    return new Promise((resolve, reject) => {
        // Obtener una referencia a la colección "usuarios" en Firestore
        const usuariosRef = collection(db, 'usuarios');

        // Consultar Firestore para encontrar el documento del usuario por su nombre de usuario
        const consulta = query(usuariosRef, where('username', '==', username), limit(1));

        // Ejecutar la consulta
        getDocs(consulta)
            .then((querySnapshot) => {
                // Verificar si se encontró algún documento
                if (!querySnapshot.empty) {
                    // Obtener el primer documento encontrado
                    const userData = querySnapshot.docs[0].data();
                    resolve(userData);
                } else {
                    resolve(null); // No se encontró ningún usuario con ese nombre de usuario
                }
            })
            .catch((error) => {
                reject(error); // Manejar cualquier error de consulta
            });
    });
}
  
export { initializeFirebase, signInWithEmailAndPassword, createUserWithEmailAndPassword, setDoc, doc, getUserByUsername, getAuth };
