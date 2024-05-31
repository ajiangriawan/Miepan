from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from functools import wraps
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from os.path import join, dirname
from dotenv import load_dotenv
import hashlib
import jwt
import random
from datetime import datetime, timedelta

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

UPLOAD_FOLDER = 'static/img/profil'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

MONGODB_CONNECTION_STRING = os.environ.get("CONNECTION")
DB_NAME = os.environ.get("DATABASE_NAME")
JWT_SECRET_KEY = os.environ.get("SECRET_KEY")

client = MongoClient(MONGODB_CONNECTION_STRING)
db = client[DB_NAME]
jobs_collection = db.jobs
users_collection = db.users

def generate_fake_sales_data(num_days):
    sales_data = []
    base_date = datetime.now()
    for i in range(num_days):
        date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
        sales = random.randint(50, 150)
        sales_data.append({"date": date, "sales": sales})
    return sales_data

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = users_collection.find_one({'email': data['email']})
            if current_user is None:
                return redirect(url_for('login'))
        except:
            return redirect(url_for('login'))
        return f(current_user, *args, **kwargs)
    return decorated

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({'email': email})

        if user and user['password'] == hashlib.sha256(password.encode()).hexdigest():
            token = jwt.encode({
                'email': email,
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, JWT_SECRET_KEY, algorithm='HS256')
            resp = redirect(url_for('profil'))
            resp.set_cookie('token', token)
            return resp
        else:
            flash('Email atau Password salah', 'danger')
            return redirect(url_for('login'))
    return render_template("login.html")

@app.route("/regis", methods=['GET', 'POST'])
def regis():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        passwordver = request.form['passwordver']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        nama = request.form['nama']

        if password == passwordver:
            if users_collection.find_one({'email': email}):
                flash('email sudah terdaftar', 'danger')
                return redirect(url_for('regis'))

            user = {
                'email': email,
                'password': hashed_password,
                'nama': nama,
                'notlp': 'silahkan edit profil',
                'alamat': 'silahkan edit profil',
                'fotoprofil': 'profil.png',
            }
            users_collection.insert_one(user)
            flash('Pendaftaran berhasil', 'success')
            return redirect(url_for('login'))
        else:
            flash('Password yang anda masukan tidak sama', 'danger')
            return redirect(url_for('regis'))
    return render_template("register.html")

@app.route('/logout')
def logout():
    resp = redirect(url_for('login'))
    resp.delete_cookie('token')
    return resp

@app.route("/menu")
def menu():
    return render_template("menu.html")

@app.route("/detail_menu")
def detailMenu():
    return render_template("detail_menu.html")

@app.route("/tentang")
def tentang():
    return render_template("tentang.html")

@app.route("/pesanan")
def pesanan():
    return render_template("pesanan.html")

@app.route("/bayar")
def bayar():
    return render_template("pembayaran.html")

@app.route("/keranjang")
def keranjang():
    return render_template("keranjang.html")

@app.route("/checkout")
def checkout():
    return render_template("checkout.html")

@app.route("/profil")
@token_required
def profil(current_user):
    return render_template("profil.html", user=current_user)

@app.route("/editProfil", methods=['GET', 'POST'])
@token_required
def editProfil(current_user):
    if request.method == 'POST':
        updated_user = {
            'nama': request.form['nama'],
            'email': request.form['email'],
            'notlp': request.form['notlp'],
            'alamat': request.form['alamat']
        }

        if 'fotoprofil' in request.files:
            file = request.files['fotoprofil']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                updated_user['fotoprofil'] = filepath

        users_collection.update_one({'_id': ObjectId(current_user['_id'])}, {'$set': updated_user})
        flash('Profil berhasil diperbarui', 'success')
        return redirect(url_for('profil'))

    return render_template("edit_profil.html", user=current_user)

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/kelolaMenu")
def kelolaMenu():
    return render_template("kelola_menu.html")

@app.route("/kelolaPesanan")
def kelolaPesanan():
    return render_template("kelola_pesanan.html")

@app.route("/kelolaRekening")
def kelolaRekening():
    return render_template("kelola_rekening.html")

@app.route("/kelolaAdmin")
def kelolaAdmin():
    return render_template("kelola_admin.html")

@app.route('/sales_data')
def sales_data():
    period = request.args.get('period', 'weekly')
    if period == 'weekly':
        sales = generate_fake_sales_data(7)
    elif period == 'monthly':
        sales = generate_fake_sales_data(30)
    elif period == 'yearly':
        sales = generate_fake_sales_data(365)
    return jsonify(sales)

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
