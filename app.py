from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_mail import Mail, Message
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

# Configuration Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)

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
    Envoie l'OTP par email
    """
    try:
        print(f"📧 Tentative d'envoi d'email à {email}")
        print(f"   MAIL_SERVER: {app.config['MAIL_SERVER']}")
        print(f"   MAIL_PORT: {app.config['MAIL_PORT']}")
        print(f"   MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
        print(f"   OTP: {otp}")
        
        msg = Message(
            subject='Votre code OTP',
            recipients=[email],
            html=f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #FFF9F7;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <h2 style="color: #FF9A8B; margin-bottom: 20px;">Votre code de vérification</h2>
                        <p style="font-size: 16px; color: #333; margin-bottom: 20px;">
                            Utilisez le code suivant pour vous connecter :
                        </p>
                        <div style="background-color: #FFF9F7; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0;">
                            <h1 style="color: #FF9A8B; font-size: 36px; letter-spacing: 8px; margin: 0;">
                                {otp}
                            </h1>
                        </div>
                        <p style="font-size: 14px; color: #666;">
                            Ce code est valide pendant <strong>10 minutes</strong>.
                        </p>
                        <p style="font-size: 14px; color: #666; margin-top: 20px;">
                            Si vous n'avez pas demandé ce code, ignorez cet email.
                        </p>
                    </div>
                </body>
            </html>
            """
        )
        
        print("📨 Envoi de l'email en cours...")
        mail.send(msg)
        print(f"✅ Email OTP envoyé avec succès à {email}")
        return True
    except Exception as e:
        print(f"❌ ERREUR lors de l'envoi de l'email:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
        # Afficher l'OTP dans le terminal comme fallback
        print(f"📧 OTP pour {email}: {otp}")
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sign')
def sign():
    mode = request.args.get('mode', 'signin')
    auth_method = request.args.get('auth_method', 'password')
    return render_template('sign.html', mode=mode, auth_method=auth_method)

@app.route('/account')
def myAccount():
    if 'user_id' not in session:
        return redirect(url_for('sign'))
    
    user_result = supabase.table('users')\
        .select('id, name, email, created_at')\
        .eq('id', session['user_id'])\
        .execute()
    
    user = user_result.data[0] if user_result.data else None
    
    return render_template('myaccount.html', user=user)

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

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Déconnexion de l'utilisateur"""
    session.clear()
    if request.method == 'POST':
        return jsonify({'success': True, 'message': 'Déconnexion réussie'})
    return redirect('/sign')

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

@app.route('/api/passwords', methods=['GET'])
def get_passwords():
    """Récupérer tous les mots de passe de l'utilisateur connecté"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non authentifié'}), 401
    
    try:
        passwords_result = supabase.table('saved_passwords')\
            .select('*')\
            .eq('user_id', session['user_id'])\
            .order('created_at', desc=True)\
            .execute()
        
        return jsonify({
            'success': True,
            'passwords': passwords_result.data if passwords_result.data else []
        })
    except Exception as e:
        print(f"Erreur lors de la récupération des mots de passe: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/passwords', methods=['POST'])
def api_save_password():
    """Sauvegarder un nouveau mot de passe via API JSON"""
    if 'user_id' not in session:
        print("❌ Utilisateur non authentifié")
        return jsonify({'success': False, 'message': 'Non authentifié'}), 401
    
    try:
        data = request.json
        site_url = data.get('site_url')
        password = data.get('password')
        description = data.get('description', '')
        
        print(f"📝 Tentative de sauvegarde:")
        print(f"   User ID: {session['user_id']}")
        print(f"   Site URL: {site_url}")
        print(f"   Password: {password[:5]}..." if password else "   Password: None")
        print(f"   Description: {description}")
        
        if not site_url or not password:
            print("❌ URL ou mot de passe manquant")
            return jsonify({'success': False, 'message': 'URL et mot de passe requis'}), 400
        
        # Sauvegarder le mot de passe
        print("💾 Insertion dans Supabase...")
        result = supabase.table('saved_passwords').insert({
            'user_id': session['user_id'],
            'password': password,
            'site_url': site_url,
            'description': description
        }).execute()
        
        print(f"✅ Résultat Supabase: {result.data}")
        
        if result.data and len(result.data) > 0:
            print(f"✅ Mot de passe sauvegardé avec succès: {result.data[0]['id']}")
            return jsonify({
                'success': True,
                'password': result.data[0]
            })
        else:
            print("❌ Aucune donnée retournée par Supabase")
            return jsonify({'success': False, 'message': 'Erreur lors de la sauvegarde'}), 500
        
    except Exception as e:
        print(f"💥 ERREUR lors de la sauvegarde du mot de passe:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/passwords/<password_id>', methods=['DELETE'])
def api_delete_password(password_id):
    """Supprimer un mot de passe via API"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non authentifié'}), 401
    
    try:
        # Supprimer uniquement si le mot de passe appartient à l'utilisateur
        supabase.table('saved_passwords')\
            .delete()\
            .eq('id', password_id)\
            .eq('user_id', session['user_id'])\
            .execute()
        
        print(f"✅ Mot de passe {password_id} supprimé")
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Erreur lors de la suppression: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Route de debug (à supprimer en production)
@app.route('/debug/routes')
def show_routes():
    """Afficher toutes les routes disponibles"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
            'path': str(rule)
        })
    
    html = '<h1>Routes disponibles</h1><table border="1" cellpadding="10">'
    html += '<tr><th>Endpoint</th><th>Methods</th><th>Path</th></tr>'
    for route in sorted(routes, key=lambda x: x['path']):
        html += f"<tr><td>{route['endpoint']}</td><td>{route['methods']}</td><td>{route['path']}</td></tr>"
    html += '</table>'
    return html

# Route de test email (à supprimer en production)
@app.route('/test-email')
def test_email():
    """Route de test pour l'envoi d'email"""
    try:
        msg = Message(
            subject='Test MyMDP',
            recipients=[os.getenv('MAIL_USERNAME')],
            body='Ceci est un email de test. Si vous le recevez, la configuration fonctionne !'
        )
        mail.send(msg)
        return "Email envoyé avec succès ! Vérifiez votre boîte de réception."
    except Exception as e:
        return f"Erreur: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)

# Pour Vercel (important !)
handler = app
