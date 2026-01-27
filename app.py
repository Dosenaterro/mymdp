from flask import Flask, request, jsonify, render_template, session
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
SUPABASE_URL = os.getenv('https://ufzpkwrfvvmprvfwufrx.supabase.co')
SUPABASE_KEY = os.getenv('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVmenBrd3JmdnZtcHJ2Znd1ZnJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0NDMxNTMsImV4cCI6MjA4NTAxOTE1M30.VDqeMeUQyeMpOPctABGR1J8Go-zSqGX_OC78LcSCSZI')

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sign')
def sign():
    return render_template('sign.html')

@app.route('/send-otp', methods=['POST'])
def send_otp():
    """Génère et envoie un OTP à l'email de l'utilisateur"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email requis'}), 400
        
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
        
        return jsonify({
            'success': True,
            'message': 'OTP envoyé avec succès'
        })
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'OTP: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de l\'envoi de l\'OTP'
        }), 500

@app.route('/signin', methods=['POST'])
def signin():
    """Connexion de l'utilisateur avec mot de passe ou OTP"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        otp = data.get('otp')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email requis'}), 400
        
        # Vérification avec OTP
        if otp:
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
                    return jsonify({
                        'success': True,
                        'user': user_result.data[0]
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Utilisateur non trouvé'
                    }), 404
            else:
                return jsonify({
                    'success': False,
                    'message': 'OTP invalide ou expiré'
                }), 401
        
        # Vérification avec mot de passe
        elif password:
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
                return jsonify({
                    'success': True,
                    'user': user_result.data[0]
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Email ou mot de passe incorrect'
                }), 401
        
        else:
            return jsonify({
                'success': False,
                'message': 'Mot de passe ou OTP requis'
            }), 400
            
    except Exception as e:
        print(f"Erreur lors de la connexion: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la connexion'
        }), 500

@app.route('/signup', methods=['POST'])
def signup():
    """Inscription d'un nouvel utilisateur"""
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not name or not email or not password:
            return jsonify({
                'success': False,
                'message': 'Tous les champs sont requis'
            }), 400
        
        # Vérifier si l'email existe déjà
        existing_user = supabase.table('users')\
            .select('id')\
            .eq('email', email)\
            .execute()
        
        if existing_user.data and len(existing_user.data) > 0:
            return jsonify({
                'success': False,
                'message': 'Cet email est déjà utilisé'
            }), 409
        
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
            return jsonify({
                'success': True,
                'message': 'Compte créé avec succès',
                'user': {
                    'id': result.data[0]['id'],
                    'name': name,
                    'email': email
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erreur lors de la création du compte'
            }), 500
            
    except Exception as e:
        print(f"Erreur lors de l'inscription: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la création du compte'
        }), 500

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