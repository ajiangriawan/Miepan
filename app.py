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
from collections import defaultdict

# Load environment variables
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

# Directories for image uploads
UPLOAD_FOLDER = 'static/img/profil'
MENU_FOLDER = 'static/img/menu'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MENU_FOLDER'] = MENU_FOLDER

# Create upload directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MENU_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# MongoDB connection
MONGODB_CONNECTION_STRING = os.environ.get("CONNECTION")
DB_NAME = os.environ.get("DATABASE_NAME")
JWT_SECRET_KEY = os.environ.get("SECRET_KEY")

client = MongoClient(MONGODB_CONNECTION_STRING)
db = client[DB_NAME]
jobs_collection = db.jobs
users_collection = db.users
menus_collection = db.menus
sales_collection = db.sales
categories_collection = db.categories
carts_collection = db.carts

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
        except jwt.ExpiredSignatureError:
            return redirect(url_for('login'))
        except jwt.InvalidTokenError:
            return redirect(url_for('login'))
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = users_collection.find_one({'email': data['email']})
            if current_user is None or current_user.get('role') != 'admin':
                return redirect(url_for('login'))
        except jwt.ExpiredSignatureError:
            return redirect(url_for('login'))
        except jwt.InvalidTokenError:
            return redirect(url_for('login'))
        return f(current_user, *args, **kwargs)
    return decorated

def get_user_role():
    token = request.cookies.get('token')
    if token:
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            user = users_collection.find_one({'email': data['email']})
            if user:
                return user.get('role', 'user')
        except:
            return 'user'
    return 'user'

@app.route('/')
def index():
    menus = menus_collection.find().limit(3)
    menu_list = list(menus)
    user_role = get_user_role()
    return render_template('index.html', user_role=user_role, menus=menu_list)

@app.route("/login", methods=['GET', 'POST'])
def login():
    user_role = get_user_role()
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
    return render_template("login.html", user_role=user_role)

@app.route("/regis", methods=['GET', 'POST'])
def regis():
    user_role = get_user_role()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        passwordver = request.form['passwordver']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        nama = request.form['nama']

        if password == passwordver:
            if users_collection.find_one({'email': email}):
                flash('Email sudah terdaftar', 'danger')
                return redirect(url_for('regis'))

            user = {
                'email': email,
                'password': hashed_password,
                'nama': nama,
                'notlp': 'silahkan edit profil',
                'alamat': 'silahkan edit profil',
                'fotoprofil': 'static/img/profil/profil.png',
                'role': 'pelanggan',
            }
            users_collection.insert_one(user)
            flash('Pendaftaran berhasil', 'success')
            return redirect(url_for('login'))
        else:
            flash('Password yang anda masukan tidak sama', 'danger')
            return redirect(url_for('regis'))
    return render_template("register.html", user_role=user_role)

@app.route('/logout')
@token_required
def logout(current_user):
    resp = redirect(url_for('login'))
    resp.delete_cookie('token')
    return resp

@app.route("/menu")
def menu():
    category = request.args.get('category')
    if category:
        menus = menus_collection.find({'kategorimenu': category})
    else:
        menus = menus_collection.find()
    menu_list = list(menus)
    user_role = get_user_role()

    categories = list(categories_collection.find())  # Get categories from the categories collection
    return render_template("menu.html", user_role=user_role, menus=menu_list, categories=categories)

@app.route("/detail_menu/<menu_id>", methods=['GET', 'POST'])
def detailMenu(menu_id):
    user_role = get_user_role()
    menu = menus_collection.find_one({'_id': ObjectId(menu_id)})
    
    if menu:
        # Find a random menu item from a different category
        different_category_menu = menus_collection.aggregate([
            {"$match": {"kategorimenu": {"$ne": menu['kategorimenu']}}},
            {"$sample": {"size": 1}}
        ])
        different_category_menu = list(different_category_menu)  # convert cursor to list
        if different_category_menu:
            different_category_menu = different_category_menu[0]
        else:
            different_category_menu = None  # Handle case where no other categories are available
    else:
        different_category_menu = None
    
    return render_template("detail_menu.html", user_role=user_role, menu=menu, different_category_menu=different_category_menu)


@app.route("/tentang")
def tentang():
    user_role = get_user_role()
    return render_template("tentang.html", user_role=user_role)

@app.route("/pesanan")
@token_required
def pesanan(current_user):
    user_role = get_user_role()
    return render_template("pesanan.html", user=current_user, user_role=user_role)

@app.route("/bayar")
@token_required
def bayar(current_user):
    user_role = get_user_role()
    return render_template("pembayaran.html", user=current_user, user_role=user_role)

@app.route("/keranjang")
@token_required
def keranjang(current_user):
    user_role = get_user_role()
    carts = carts_collection.find({'user_id': current_user['_id']})
    cart_items = list(carts)
    return render_template("keranjang.html", user=current_user, user_role=user_role, cart_items=cart_items)

@app.route('/keranjang/<menu_id>', methods=['POST'])
@token_required
def add_to_cart(current_user, menu_id):
    user_role = get_user_role()
    menu = menus_collection.find_one({'_id': ObjectId(menu_id)})
    if menu:
        cart_item = {
            'user_id': current_user['_id'],
            'menu_id': menu['_id'],
            'quantity': 1,
            'namamenu': menu['namamenu'],
            'hargamenu': menu['hargamenu'],
            'fotomenu': menu['fotomenu']
        }
        carts_collection.insert_one(cart_item)
        flash('Menu ditambahkan ke keranjang', 'success')
    else:
        flash('Menu tidak ditemukan', 'danger')
    return redirect(url_for('menu'))

@app.route('/cart_count', methods=['GET'])
@token_required
def cart_count(current_user):
    # Mengambil user_id dari current_user yang diambil dari token
    user_id = current_user['_id']
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Menghitung jumlah dokumen/item dalam koleksi yang sesuai dengan user_id
    total_items = carts_collection.count_documents({'user_id': user_id})

    return jsonify({'total_items': total_items})


@app.route("/checkout")
@token_required
def checkout(current_user):
    user_role = get_user_role()
    return render_template("checkout.html", user=current_user, user_role=user_role)

@app.route("/profil")
@token_required
def profil(current_user):
    user_role = get_user_role()
    return render_template("profil.html", user=current_user, user_role=user_role)

@app.route("/editProfil", methods=['GET', 'POST'])
@token_required
def editProfil(current_user):
    user_role = get_user_role()
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

    return render_template("edit_profil.html", user=current_user, user_role=user_role)

@app.route("/dashboard")
@admin_required
def dashboard(current_user):
    user_role = get_user_role()

    users = users_collection.find()
    menus = menus_collection.find()
    sales = sales_collection.find()

    user_list = list(users)
    menu_list = list(menus)
    sale_list = list(sales)

    total_menus = len(menu_list)
    total_sales = sum(sale['sales'] for sale in sale_list)
    count_per_role = defaultdict(int)

    for user in user_list:
        role = user.get('role', 'Uncategorized')
        count_per_role[role] += 1

    return render_template("dashboard.html", user_role=user_role, menus=menu_list, total_menus=total_menus, count_per_role=count_per_role, total_sales=total_sales)

@app.route('/kelolaMenu')
@admin_required
def kelolaMenu(current_user):
    user_role = get_user_role()
    menus = menus_collection.find()
    menu_list = list(menus)

    count_per_category = defaultdict(int)
    total_menus = 0

    for menu in menu_list:
        category = menu.get('kategorimenu', 'Uncategorized')
        count_per_category[category] += 1
        total_menus += 1

    return render_template('kelola_menu.html', user_role=user_role, menus=menu_list, count_per_category=count_per_category, total_menus=total_menus)

@app.route("/tambahMenu", methods=['POST'])
@admin_required
def tambahMenu(current_user):
    tambahmenu = {
        'namamenu': request.form['namaMenu'],
        'hargamenu': request.form['hargaMenu'],
        'deskripsimenu': request.form['deskripsiMenu'],
        'kategorimenu': request.form['kategoriMenu']
    }

    file = request.files['fotoMenu']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['MENU_FOLDER'], filename)
        file.save(filepath)
        tambahmenu['fotomenu'] = filepath

    menus_collection.insert_one(tambahmenu)
    flash('Tambah menu berhasil', 'success')
    return redirect(url_for('kelolaMenu'))

@app.route("/editMenu/<menu_id>", methods=['GET', 'POST'])
@admin_required
def editMenu(current_user, menu_id):
    user_role = get_user_role()
    menu = menus_collection.find_one({'_id': ObjectId(menu_id)})

    if request.method == 'POST':
        updated_menu = {
            'namamenu': request.form['namaMenu'],
            'hargamenu': request.form['hargaMenu'],
            'deskripsimenu': request.form['deskripsiMenu'],
            'kategorimenu': request.form['kategoriMenu']
        }

        if 'fotoMenu' in request.files:
            file = request.files['fotoMenu']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['MENU_FOLDER'], filename)
                file.save(filepath)
                updated_menu['fotomenu'] = filepath

        menus_collection.update_one({'_id': ObjectId(menu_id)}, {'$set': updated_menu})
        flash('Menu berhasil diperbarui', 'success')
        return redirect(url_for('kelolaMenu'))

    return render_template("edit_menu.html", user_role=user_role, menu=menu)

@app.route("/hapusMenu/<menu_id>", methods=['POST'])
@admin_required
def hapusMenu(current_user, menu_id):
    try:
        menus_collection.delete_one({'_id': ObjectId(menu_id)})
        flash('Menu berhasil dihapus', 'success')
    except Exception as e:
        flash(f'Gagal menghapus menu: {str(e)}', 'danger')
    return redirect(url_for('kelolaMenu'))

@app.route("/kelolaPesanan")
@admin_required
def kelolaPesanan(current_user):
    user_role = get_user_role()
    return render_template("kelola_pesanan.html", user_role=user_role)

@app.route("/kelolaRekening")
@admin_required
def kelolaRekening(current_user):
    user_role = get_user_role()
    return render_template("kelola_rekening.html", user_role=user_role)

@app.route("/kelolaAdmin")
@admin_required
def kelolaAdmin(current_user):
    user_role = get_user_role()
    return render_template("kelola_admin.html", user_role=user_role)

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
