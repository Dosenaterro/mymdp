from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import random
import string
from datetime import datetime, timedelta
import hashlib


# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Configuration Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Les variables SUPABASE_URL et SUPABASE_KEY doivent être définies dans le fichier .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_otp():
    """Génère un OTP à 6 chiffres"""
    return ''.join(random.choices(string.digits, k=6))

def hash_password(password):
    """Hash le mot de passe avec SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def send_email_otp(email, otp):
    """
    Fonction pour envoyer l'OTP par email
    À implémenter avec un service comme SendGrid, Mailgun, etc.
    """
    print(f"📧 OTP {otp} envoyé à {email}")
    # TODO: Implémenter l'envoi réel d'email
    return True

#Differentes pages
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/account')
def myAccount():
    if 'user_id' not in session:
        return redirect(url_for('sign'))
        
    return render_template('myaccount.html')
    
@app.route('/sign')
def sign():
    mode = request.args.get('mode', 'signin')
    auth_method = request.args.get('auth_method', 'password')
    return render_template('sign.html', mode=mode, auth_method=auth_method)

@app.route('/sign/send-otp', methods=['POST'])
def send_otp():
    """Génère et envoie un OTP à l'email de l'utilisateur"""
    try:
        email = request.form.get('email')
        
        if not email:
            return render_template('sign.html', 
                                 mode='signin',
                                 auth_method='otp',
                                 error='Email requis',
                                 email=email)
        
        # Générer l'OTP
        otp = generate_otp()
        
        # Supprimer les anciens OTP pour cet email
        supabase.table('otp_codes').delete().eq('email', email).execute()
        
        # Enregistrer le nouvel OTP dans Supabase
        expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
        
        result = supabase.table('otp_codes').insert({
            'email': email,
            'otp': otp,
            'expires_at': expires_at
        }).execute()
        
        # Envoyer l'OTP par email
        send_email_otp(email, otp)
        
        return render_template('sign.html',
                             mode='signin',
                             auth_method='otp',
                             otp_sent=True,
                             email=email,
                             info=f'OTP envoyé à {email}')
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'OTP: {str(e)}")
        return render_template('sign.html',
                             mode='signin',
                             auth_method='otp',
                             error='Erreur lors de l\'envoi de l\'OTP',
                             email=email)

@app.route('/sign/verify-otp', methods=['POST'])
def verify_otp():
    """Vérifie l'OTP et connecte l'utilisateur"""
    try:
        email = request.form.get('email')
        otp = request.form.get('otp')
        
        if not email or not otp:
            return render_template('sign.html',
                                 mode='signin',
                                 auth_method='otp',
                                 otp_sent=True,
                                 email=email,
                                 error='Email et OTP requis')
        
        # Récupérer l'OTP valide pour cet email
        otp_result = supabase.table('otp_codes')\
            .select('*')\
            .eq('email', email)\
            .eq('otp', otp)\
            .gte('expires_at', datetime.now().isoformat())\
            .execute()
        
        if otp_result.data and len(otp_result.data) > 0:
            # OTP valide - supprimer l'OTP utilisé
            supabase.table('otp_codes').delete().eq('email', email).execute()
            
            # Vérifier si l'utilisateur existe
            user_result = supabase.table('users')\
                .select('id, name, email')\
                .eq('email', email)\
                .execute()
            
            if user_result.data and len(user_result.data) > 0:
                session['user_id'] = user_result.data[0]['id']
                session['user_email'] = email
                return redirect('/account')
            else:
                return render_template('sign.html',
                                     mode='signin',
                                     auth_method='otp',
                                     otp_sent=True,
                                     email=email,
                                     error='Utilisateur non trouvé')
        else:
            return render_template('sign.html',
                                 mode='signin',
                                 auth_method='otp',
                                 otp_sent=True,
                                 email=email,
                                 error='OTP invalide ou expiré')
            
    except Exception as e:
        print(f"Erreur lors de la vérification de l'OTP: {str(e)}")
        return render_template('sign.html',
                             mode='signin',
                             auth_method='otp',
                             otp_sent=True,
                             email=email,
                             error='Erreur lors de la vérification')

@app.route('/sign/signin', methods=['POST'])
def signin():
    """Connexion de l'utilisateur avec mot de passe"""
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template('sign.html',
                                 mode='signin',
                                 error='Email et mot de passe requis',
                                 email=email)
        
        hashed_password = hash_password(password)
        
        # Vérifier les credentials
        user_result = supabase.table('users')\
            .select('id, name, email')\
            .eq('email', email)\
            .eq('password', hashed_password)\
            .execute()
        
        if user_result.data and len(user_result.data) > 0:
            session['user_id'] = user_result.data[0]['id']
            session['user_email'] = email
            return redirect('/account')
        else:
            return render_template('sign.html',
                                 mode='signin',
                                 error='Email ou mot de passe incorrect',
                                 email=email)
            
    except Exception as e:
        print(f"Erreur lors de la connexion: {str(e)}")
        return render_template('sign.html',
                             mode='signin',
                             error='Erreur lors de la connexion',
                             email=email)

@app.route('/sign/signup', methods=['POST'])
def signup():
    """Inscription d'un nouvel utilisateur"""
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not name or not email or not password or not confirm_password:
            return render_template('sign.html',
                                 mode='signup',
                                 error='Tous les champs sont requis',
                                 name=name,
                                 email=email)
        
        if password != confirm_password:
            return render_template('sign.html',
                                 mode='signup',
                                 error='Les mots de passe ne correspondent pas',
                                 name=name,
                                 email=email)
        
        if len(password) < 6:
            return render_template('sign.html',
                                 mode='signup',
                                 error='Le mot de passe doit contenir au moins 6 caractères',
                                 name=name,
                                 email=email)
        
        # Vérifier si l'email existe déjà
        existing_user = supabase.table('users')\
            .select('id')\
            .eq('email', email)\
            .execute()
        
        if existing_user.data and len(existing_user.data) > 0:
            return render_template('sign.html',
                                 mode='signup',
                                 error='Cet email est déjà utilisé',
                                 name=name,
                                 email=email)
        
        # Hash le mot de passe
        hashed_password = hash_password(password)
        
        # Créer le nouvel utilisateur
        result = supabase.table('users').insert({
            'name': name,
            'email': email,
            'password': hashed_password
        }).execute()
        
        if result.data and len(result.data) > 0:
            print(f"✅ Nouvel utilisateur créé: {name} ({email})")
            # Rediriger vers la section signin avec un message de succès
            return render_template('sign.html',
                                 mode='signin',
                                 success='Compte créé avec succès ! Vous pouvez maintenant vous connecter.',
                                 email=email)
        else:
            return render_template('sign.html',
                                 mode='signup',
                                 error='Erreur lors de la création du compte',
                                 name=name,
                                 email=email)
            
    except Exception as e:
        print(f"Erreur lors de l'inscription: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('sign.html',
                             mode='signup',
                             error=f'Erreur: {str(e)}',
                             name=name,
                             email=email)

@app.route('/logout', methods=['POST'])
def logout():
    """Déconnexion de l'utilisateur"""
    session.clear()
    return jsonify({'success': True, 'message': 'Déconnexion réussie'})

@app.route('/user', methods=['GET'])
def get_user():
    """Récupère les informations de l'utilisateur connecté"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non authentifié'}), 401
    
    try:
        user_result = supabase.table('users')\
            .select('id, name, email, created_at')\
            .eq('id', session['user_id'])\
            .execute()
        
        if user_result.data and len(user_result.data) > 0:
            return jsonify({
                'success': True,
                'user': user_result.data[0]
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }), 404
            
    except Exception as e:
        print(f"Erreur lors de la récupération de l'utilisateur: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erreur serveur'
        }), 500

# Fonction de nettoyage des OTP expirés (à exécuter périodiquement)
@app.route('/cleanup-otp', methods=['POST'])
def cleanup_expired_otp():
    """Supprime les OTP expirés de la base de données"""
    try:
        result = supabase.table('otp_codes')\
            .delete()\
            .lt('expires_at', datetime.now().isoformat())\
            .execute()
        
        return jsonify({
            'success': True,
            'message': f'OTP expirés supprimés'
        })
    except Exception as e:
        print(f"Erreur lors du nettoyage des OTP: {str(e)}")
        return jsonify({'success': False, 'message': 'Erreur'}), 500

if __name__ == '__main__':
    app.run(debug=True)