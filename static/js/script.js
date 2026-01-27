// Toggle entre Sign In et Sign Up
document.getElementById('signInBtn').addEventListener('click', () => {
    document.getElementById('signInSection').classList.add('active');
    document.getElementById('signUpSection').classList.remove('active');
    document.getElementById('signInBtn').classList.add('active');
    document.getElementById('signUpBtn').classList.remove('active');
});

document.getElementById('signUpBtn').addEventListener('click', () => {
    document.getElementById('signUpSection').classList.add('active');
    document.getElementById('signInSection').classList.remove('active');
    document.getElementById('signUpBtn').classList.add('active');
    document.getElementById('signInBtn').classList.remove('active');
});

// Gestion de l'OTP
document.getElementById('getOtpBtn').addEventListener('click', () => {
    const email = document.getElementById('signInEmail').value;
    if (!email) {
        alert('Veuillez entrer votre email.');
        return;
    }
    // Envoi de l'OTP au backend (simulé ici)
    fetch('/send-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('otpGroup').style.display = 'block';
            document.getElementById('passwordGroup').style.display = 'none';
            alert('OTP envoyé à votre email.');
        } else {
            alert('Erreur lors de l\'envoi de l\'OTP.');
        }
    });
});

// Basculer vers l'authentification par mot de passe
document.getElementById('continueWithPasswordBtn').addEventListener('click', () => {
    document.getElementById('passwordGroup').style.display = 'block';
    document.getElementById('otpGroup').style.display = 'none';
});

// Soumission des formulaires
document.getElementById('signInForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('signInEmail').value;
    const password = document.getElementById('signInPassword').value;
    const otp = document.getElementById('otpInput').value;

    const data = otp ? { email, otp } : { email, password };

    fetch('/signin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Connexion réussie !');
        } else {
            alert('Erreur de connexion.');
        }
    });
});

document.getElementById('signUpForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const name = document.getElementById('signUpName').value;
    const email = document.getElementById('signUpEmail').value;
    const password = document.getElementById('signUpPassword').value;
    const confirmPassword = document.getElementById('signUpConfirmPassword').value;

    if (password !== confirmPassword) {
        alert('Les mots de passe ne correspondent pas.');
        return;
    }

    fetch('/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Inscription réussie !');
        } else {
            alert('Erreur lors de l\'inscription.');
        }
    });
});


const popup = document.getElementById('popup');
const iframe = document.getElementById('popup-iframe');

// Ouvrir la pop-up avec une URL
function openPopup(url) {
    iframe.src = url;
    popup.style.display = 'block';
    document.body.style.overflow = 'hidden'; // Empêche le scroll de la page A
}

// Fermer la pop-up
function closePopup() {
    popup.style.display = 'none';
    iframe.src = ''; // Vider l'iframe
    document.body.style.overflow = 'auto'; // Réactive le scroll
}

// Fermer en cliquant en dehors
window.addEventListener('click', function(event) {
    if (event.target === popup) {
        closePopup();
    }
});

// Fermer avec la touche Échap
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && popup.style.display === 'block') {
        closePopup();
    }
});
