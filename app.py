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
from pymongo import DESCENDING
from bson.json_util import dumps
from bson import ObjectId
from datetime import datetime
from flask import jsonify, request
import random

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
reviews_collection = db.reviews


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

def generate_order_number(user_name):
    current_time = datetime.now()
    order_date = current_time.strftime("%d%m%Y")
    order_count = sales_collection.count_documents({})
    order_number = f"{user_name[:2].upper()}{order_date}{order_count + 1}"
    return order_number

def format_rupiah(value):
    try:
        value = float(value)
        return f"Rp {value:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "Rp 0"  # atau nilai default yang sesuai jika tidak bisa dikonversi

app.jinja_env.filters['rupiah'] = format_rupiah

@app.route('/')
def index():
    menus = menus_collection.find().limit(3)
    reviews_cursor = list(reviews_collection.aggregate([{ '$sample': { 'size': 3 } }]))
    
    reviews = []
    for review in reviews_cursor:
        user = users_collection.find_one({'_id': review['user_id']})
        review['user_name'] = user['nama'] if user else 'Unknown User'
        review['user_foto'] = user['fotoprofil']
        reviews.append(review)
    
    random.shuffle(reviews)  # Acak urutan review
    
    menu_list = list(menus)
    user_role = get_user_role()

    # Mengambil semua review
    reviews = list(reviews_collection.find())
    
    # Menghitung rating rata-rata untuk setiap menu
    menu_ratings = {}
    for review in reviews:
        menu_id = review['menu_id']
        rating = review['rating']
        
        menu_id = str(menu_id)
        
        if menu_id in menu_ratings:
            menu_ratings[menu_id]['total_rating'] += rating
            menu_ratings[menu_id]['count'] += 1
        else:
            menu_ratings[menu_id] = {'total_rating': rating, 'count': 1}
    
    for menu in menu_list:
        menu_id = str(menu['_id'])
        if menu_id in menu_ratings:
            total_rating = menu_ratings[menu_id]['total_rating']
            count = menu_ratings[menu_id]['count']
            menu['average_rating'] = total_rating / count
        else:
            menu['average_rating'] = None

    return render_template('index.html', user_role=user_role, menus=menu_list, reviews=reviews)

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
    
    # Mengambil semua review
    reviews = list(reviews_collection.find())
    
    # Menghitung rating rata-rata untuk setiap menu
    menu_ratings = {}
    for review in reviews:
        menu_id = review['menu_id']
        rating = review['rating']
        
        menu_id = str(menu_id)
        
        if menu_id in menu_ratings:
            menu_ratings[menu_id]['total_rating'] += rating
            menu_ratings[menu_id]['count'] += 1
        else:
            menu_ratings[menu_id] = {'total_rating': rating, 'count': 1}
    
    for menu in menu_list:
        menu_id = str(menu['_id'])
        if menu_id in menu_ratings:
            total_rating = menu_ratings[menu_id]['total_rating']
            count = menu_ratings[menu_id]['count']
            menu['average_rating'] = total_rating / count
        else:
            menu['average_rating'] = None
    
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

    # Mengambil semua review untuk menu tertentu
    reviews_cursor = reviews_collection.find({'menu_id': ObjectId(menu_id)})
    
    reviews = []
    total_rating = 0
    count = 0
    
    for review in reviews_cursor:
        user = users_collection.find_one({'_id': review['user_id']})
        review['user_name'] = user['nama'] if user else 'Unknown User'
        review['user_foto'] = user['fotoprofil']
        reviews.append(review)
        total_rating += review['rating']
        count += 1
    
    average_rating = total_rating / count if count > 0 else None
    
    # Menambahkan rating ke menu
    menu['average_rating'] = average_rating

    return render_template("detail_menu.html", user_role=user_role, menu=menu, different_category_menu=different_category_menu, reviews=reviews)

@app.route("/tentang")
def tentang():
    user_role = get_user_role()
    return render_template("tentang.html", user_role=user_role)

@app.route("/pesanan")
@token_required
def pesanan(current_user):
    user_role = get_user_role()
    user_id = current_user['_id']
    belum_dibayar = list(sales_collection.find({'user_id': user_id, 'status': 'belum dibayar'}))
    menunggu_konfirmasi = list(sales_collection.find({'user_id': user_id, 'status': 'menunggu konfirmasi'}))
    proses = list(sales_collection.find({'user_id': user_id, 'status': 'proses'}))
    selesai = list(sales_collection.find({'user_id': user_id, 'status': 'selesai'}))

    # Fetch reviews and organize into reviews_dict
    reviews = reviews_collection.find()
    reviews_dict = {}
    for review in reviews:
        order_number = review['order_number']
        if order_number in reviews_dict:
            reviews_dict[order_number].append(review)
        else:
            reviews_dict[order_number] = [review]

    return render_template("pesanan.html", user=current_user, user_role=user_role, belum_dibayar=belum_dibayar, menunggu_konfirmasi=menunggu_konfirmasi, proses=proses, selesai=selesai, reviews_dict=reviews_dict, review=review)

@app.route("/bayar")
@token_required
def bayar(current_user):
    user_role = get_user_role()
    return render_template("pembayaran.html", user=current_user, user_role=user_role)

@app.route('/keranjang')
@token_required
def keranjang(current_user):
    user_role = get_user_role()
    carts = carts_collection.find({'user_id': current_user['_id']}).sort('created_at', DESCENDING)
    cart_items = list(carts)
    # Ensure all prices and quantities are integers
    for item in cart_items:
        item['hargamenu'] = int(item['hargamenu'])
        item['quantity'] = int(item['quantity'])
        item['checked'] = True  # Set 'checked' field to True for rendering checkbox as checked
    return render_template("keranjang.html", user=current_user, user_role=user_role, cart_items=cart_items)

@app.route('/keranjang/<menu_id>', methods=['POST'])
@token_required
def add_to_cart(current_user, menu_id):
    user_role = get_user_role()
    menu = menus_collection.find_one({'_id': ObjectId(menu_id)})
    
    if menu:
        existing_cart_item = carts_collection.find_one({
            'user_id': current_user['_id'],
            'menu_id': menu['_id']
        })
        
        if existing_cart_item:
            new_quantity = existing_cart_item['quantity'] + 1
            carts_collection.update_one(
                {'_id': existing_cart_item['_id']},
                {'$set': {'quantity': new_quantity}}
            )
            flash('Jumlah item di keranjang diperbarui', 'success')
        else:
            cart_item = {
                'user_id': current_user['_id'],
                'menu_id': menu['_id'],
                'quantity': 1,
                'namamenu': menu['namamenu'],
                'hargamenu': menu['hargamenu'],
                'fotomenu': menu['fotomenu'],
                'created_at': datetime.now(),
            }
            carts_collection.insert_one(cart_item)
            flash('Menu ditambahkan ke keranjang', 'success')
    else:
        flash('Menu tidak ditemukan', 'danger')
    
    return redirect(url_for('menu'))

@app.route('/update_quantity/<item_id>', methods=['POST'])
@token_required
def update_quantity(current_user, item_id):
    data = request.get_json()
    action = data.get('action')
    item = carts_collection.find_one({'_id': ObjectId(item_id), 'user_id': current_user['_id']})
    
    if item:
        if action == 'increase':
            new_quantity = item['quantity'] + 1
        elif action == 'decrease' and item['quantity'] > 1:
            new_quantity = item['quantity'] - 1
        else:
            return jsonify({'success': False, 'message': 'Invalid action or quantity cannot be less than 1'})

        carts_collection.update_one({'_id': ObjectId(item_id)}, {'$set': {'quantity': new_quantity}})
        return jsonify({'success': True, 'new_quantity': new_quantity})
    else:
        return jsonify({'success': False, 'message': 'Item not found in cart'})

@app.route('/delete_item/<item_id>', methods=['DELETE'])
@token_required
def delete_item(current_user, item_id):
    result = carts_collection.delete_one({'_id': ObjectId(item_id), 'user_id': current_user['_id']})
    if result.deleted_count == 1:
        return jsonify({'success': True, 'message': 'Item berhasil dihapus'}), 200
    else:
        return jsonify({'success': False, 'message': 'Item tidak ditemukan'}), 404

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

@app.route('/checkout/<menu_id>', methods=['POST'])
@token_required
def direct_checkout(current_user, menu_id):
    menu = menus_collection.find_one({'_id': ObjectId(menu_id)})
    if menu:
        # Langsung proses checkout untuk item yang dipilih
        return redirect(url_for('checkout', menu_id=menu_id))
    else:
        flash('Menu tidak ditemukan', 'danger')
        return redirect(url_for('menu'))

def validate_cart_items(cart_items):
    for item in cart_items:
        try:
            item['hargamenu'] = float(item['hargamenu'])
            item['quantity'] = int(item['quantity'])
        except ValueError:
            return False
    return True

@app.route("/checkout", methods=['GET', 'POST'])
@token_required
def checkout(current_user):
    user_role = get_user_role()
    if request.method == 'POST':
        cart_items = list(carts_collection.find({'user_id': current_user['_id']}))
        if not validate_cart_items(cart_items):
            flash('Invalid data in cart items.', 'danger')
            return redirect(url_for('index'))

        total_amount = sum(item['hargamenu'] * item['quantity'] for item in cart_items)
        order_number = generate_order_number(current_user['nama'])
        sales_data = {
            'user_id': current_user['_id'],
            'user_name': current_user['nama'],
            'order_number': order_number,
            'order_date': datetime.now(),
            'items': cart_items,
            'total_amount': total_amount,
            'payment_method': request.form['metode_pembayaran'],
            'status':'belum dibayar'
        }

        sales_collection.insert_one(sales_data)
        carts_collection.delete_many({'user_id': current_user['_id']})

        flash('Pembayaran berhasil, terima kasih telah berbelanja!', 'success')
        return redirect(url_for('payment', order_number=order_number))
    else:
        cart_items = list(carts_collection.find({'user_id': current_user['_id']}))
        if not validate_cart_items(cart_items):
            flash('Invalid data in cart items.', 'danger')
            return redirect(url_for('index'))

        total_amount = sum(item['hargamenu'] * item['quantity'] for item in cart_items)
        return render_template("checkout.html", user=current_user, user_role=user_role, cart_items=cart_items, total_amount=total_amount)

@app.route('/payment/<order_number>', methods=['GET'])
@token_required
def payment(current_user, order_number):
    order = sales_collection.find_one({'order_number': order_number, 'user_id': current_user['_id']})
    if order:
        return render_template('pembayaran.html', order=order, user=current_user)
    else:
        flash('Order not found.', 'danger')
        return redirect(url_for('index'))

@app.route('/upload_bukti_pembayaran/<order_number>', methods=['POST'])
@token_required
def upload_bukti_pembayaran(current_user, order_number):
    if 'bukti' not in request.files:
        flash('Tidak ada file yang diunggah', 'danger')
        return redirect(url_for('payment', order_number=order_number))

    file = request.files['bukti']

    if file.filename == '':
        flash('Tidak ada file yang dipilih untuk diunggah', 'danger')
        return redirect(url_for('payment', order_number=order_number))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        bukti_folder = 'static/bukti'
        os.makedirs(bukti_folder, exist_ok=True)
        filepath = os.path.join(bukti_folder, filename)
        file.save(filepath)

        sales_collection.update_one(
            {'order_number': order_number, 'user_id': current_user['_id']},
            {'$set': {'status': 'menunggu konfirmasi', 'bukti': filepath}}
        )

        flash('Bukti pembayaran berhasil diunggah dan status pesanan diperbarui', 'success')
    else:
        flash('Jenis file tidak diizinkan', 'danger')

    return redirect(url_for('pesanan', order_number=order_number))

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
@token_required
def dashboard(current_user):
    user_role = get_user_role()

    # Query to calculate total sales and total items for completed orders
    pipeline_total_sales = [
        {'$match': {'status': 'selesai'}},  # Filter by status 'selesai'
        {'$group': {
            '_id': None,
            'total_sales': {'$sum': '$total_amount'},
            'total_items': {'$sum': {'$sum': '$items.quantity'}}
        }}
    ]

    # Execute aggregation pipeline
    sales_aggregate = list(sales_collection.aggregate(pipeline_total_sales))
    total_sales = sales_aggregate[0]['total_sales'] if sales_aggregate else 0
    total_items = sales_aggregate[0]['total_items'] if sales_aggregate else 0

    # Fetch users and menus count
    users = users_collection.find()
    menus = menus_collection.find()
    user_list = list(users)
    menu_list = list(menus)

    total_menus = len(menu_list)
    count_per_role = defaultdict(int)

    # Count users per role
    for user in user_list:
        role = user.get('role', 'Uncategorized')
        count_per_role[role] += 1

    # Render dashboard template with variables
    return render_template("dashboard.html", user_role=user_role,
                           total_sales=total_sales,
                           total_items=total_items,
                           total_menus=total_menus,
                           count_per_role=count_per_role)

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
    
    # Calculate the counts for different periods
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    today_datetime = datetime.combine(today, datetime.min.time())
    start_of_week_datetime = datetime.combine(start_of_week, datetime.min.time())
    start_of_month_datetime = datetime.combine(start_of_month, datetime.min.time())
    start_of_year_datetime = datetime.combine(start_of_year, datetime.min.time())

    daily_orders = sales_collection.count_documents({'order_date': {'$gte': today_datetime}})
    weekly_orders = sales_collection.count_documents({'order_date': {'$gte': start_of_week_datetime}})
    monthly_orders = sales_collection.count_documents({'order_date': {'$gte': start_of_month_datetime}})
    yearly_orders = sales_collection.count_documents({'order_date': {'$gte': start_of_year_datetime}})

    menunggu_konfirmasi = list(sales_collection.find({'status': 'menunggu konfirmasi'}))
    proses = list(sales_collection.find({'status': 'proses'}))
    selesai = list(sales_collection.find({'status': 'selesai'}))
    
    # Convert ObjectId to string for JSON serialization
    def convert_to_string(obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, list):
            return [convert_to_string(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_to_string(value) for key, value in obj.items()}
        else:
            return obj
    
    menunggu_konfirmasi = convert_to_string(menunggu_konfirmasi)
    proses = convert_to_string(proses)
    selesai = convert_to_string(selesai)
    
    return render_template(
        "kelola_pesanan.html", 
        user=current_user, 
        menunggu_konfirmasi=menunggu_konfirmasi, 
        proses=proses, 
        selesai=selesai,
        daily_orders=daily_orders,
        weekly_orders=weekly_orders,
        monthly_orders=monthly_orders,
        yearly_orders=yearly_orders
    )

@app.route('/detailPesanan/<order_id>', methods=['GET'])
@token_required
def detailPesanan(current_user, order_id):
    user_role = get_user_role()
    order = sales_collection.find_one({'_id': ObjectId(order_id)})
    if order:
        # Konversi ObjectId ke string dan memastikan items adalah list
        order['_id'] = str(order['_id'])
        
        items = order.get('items', [])
        if not isinstance(items, list):
            items = list(items)
        
        for item in items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
            item['menu_id'] = str(item['menu_id'])
            item['quantity'] = int(item['quantity'])
            item['hargamenu'] = float(item['hargamenu'])
        
        order['items'] = items
        
        # Debug print untuk memastikan items adalah list
        print("Order Items: ", order['items'])
        
        return render_template('detail_pesanan.html', order=order, items=items, user_role=user_role)
    else:
        flash('Order not found.', 'danger')
        return redirect(url_for('kelolaPesanan'))

@app.route('/strukPesanan/<order_id>', methods=['GET'])
@token_required
def strukPesanan(current_user, order_id):
    user_role = get_user_role()
    order = sales_collection.find_one({'_id': ObjectId(order_id)})
    if order:
        # Konversi ObjectId ke string dan memastikan items adalah list
        order['_id'] = str(order['_id'])
        
        items = order.get('items', [])
        if not isinstance(items, list):
            items = list(items)
        
        for item in items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
            item['menu_id'] = str(item['menu_id'])
            item['quantity'] = int(item['quantity'])
            item['hargamenu'] = float(item['hargamenu'])
        
        order['items'] = items
        
        # Debug print untuk memastikan items adalah list
        print("Order Items: ", order['items'])
        
        return render_template('struk.html', order=order, items=items, user_role=user_role)
    else:
        flash('Order not found.', 'danger')
        return redirect(url_for('kelolaPesanan'))

@app.route('/prosesPesanan/<order_id>')
@admin_required  
def prosesPesanan(current_user, order_id):
    try:
        sales_collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': 'proses'}}
        )
        flash('Pesanan berhasil diubah menjadi status "proses"', 'success')
    except Exception as e:
        flash(f'Gagal mengubah status pesanan: {str(e)}', 'danger')
    return redirect(url_for('kelolaPesanan'))

@app.route('/selesaiPesanan/<order_id>')
@admin_required  
def selesaiPesanan(current_user, order_id):
    try:
        sales_collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': 'selesai'}}
        )
        flash('Pesanan berhasil diubah menjadi status "selesai"', 'success')
    except Exception as e:
        flash(f'Gagal mengubah status pesanan: {str(e)}', 'danger')
    return redirect(url_for('kelolaPesanan'))

@app.route('/nilaiPesanan/<order_id>', methods=['GET'])
@token_required
def nilaiPesanan(current_user, order_id):
    order = sales_collection.find_one({'_id': ObjectId(order_id)})
    review= reviews_collection.find()
    if order:
        order['_id'] = str(order['_id'])
        items = order.get('items', [])
        for item in items:
            menu = menus_collection.find_one({'_id': ObjectId(item['menu_id'])})
            if menu:
                item['fotomenu'] = menu.get('fotomenu', '')
                item['namamenu'] = menu.get('namamenu', '')
            review = reviews_collection.find_one({'user_id': current_user['_id'], 'menu_id': ObjectId(item['menu_id'])})
            if review:
                item['review'] = {
                    '_id': str(review['_id']),
                    'rating': review['rating'],
                    'comment': review['comment']
                }
            item['_id'] = str(item['_id'])
            item['menu_id'] = str(item['menu_id'])
            item['quantity'] = int(item['quantity'])
            item['hargamenu'] = float(item['hargamenu'])
        order['items'] = items
        return render_template('nilai_pesanan.html', order=order, items=items, review=review)
    else:
        flash('Order not found.', 'danger')
        return redirect(url_for('kelolaPesanan'))

@app.route('/submit_review', methods=['POST'])
@token_required
def submit_review(current_user):
    data = request.json
    menu_id = data.get('menu_id')
    order_number = data.get('order_number')
    rating = data.get('rating')
    comment = data.get('comment')

    if not menu_id or not rating or not order_number:
        return jsonify({'success': False, 'message': 'Menu ID, Order Number, and rating are required.'}), 400

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError('Rating must be between 1 and 5.')
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    existing_review = reviews_collection.find_one({'user_id': current_user['_id'], 'menu_id': ObjectId(menu_id), 'order_number': order_number})

    if existing_review:
        try:
            reviews_collection.update_one(
                {'_id': existing_review['_id']},
                {'$set': {'rating': rating, 'comment': comment, 'timestamp': datetime.now()}}
            )
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        review = {
            'user_id': current_user['_id'],
            'menu_id': ObjectId(menu_id),
            'order_number': order_number,
            'rating': rating,
            'comment': comment,
            'timestamp': datetime.now()
        }

        try:
            reviews_collection.insert_one(review)
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    menu_reviews = list(reviews_collection.find({'menu_id': ObjectId(menu_id)}))
    if menu_reviews:
        average_rating = sum([review['rating'] for review in menu_reviews]) / len(menu_reviews)
    else:
        average_rating = 0

    menus_collection.update_one({'_id': ObjectId(menu_id)}, {'$set': {'average_rating': average_rating}})

    return jsonify({'success': True, 'message': 'Review submitted successfully.'})

@app.route('/edit_review/<review_id>', methods=['PUT'])
@token_required
def edit_review(current_user, review_id):
    data = request.json
    rating = data.get('rating')
    comment = data.get('comment')

    if not rating:
        return jsonify({'success': False, 'message': 'Rating is required.'}), 400

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError('Rating must be between 1 and 5.')
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    try:
        reviews_collection.update_one(
            {'_id': ObjectId(review_id), 'user_id': current_user['_id']},
            {'$set': {'rating': rating, 'comment': comment, 'timestamp': datetime.now()}}
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

    review = reviews_collection.find_one({'_id': ObjectId(review_id)})
    menu_id = review['menu_id']

    menu_reviews = list(reviews_collection.find({'menu_id': ObjectId(menu_id)}))
    if menu_reviews:
        average_rating = sum([review['rating'] for review in menu_reviews]) / len(menu_reviews)
    else:
        average_rating = 0

    menus_collection.update_one({'_id': ObjectId(menu_id)}, {'$set': {'average_rating': average_rating}})

    return jsonify({'success': True, 'message': 'Review edited successfully.'})

@app.route("/kelolaRekening")
@admin_required
def kelolaRekening(current_user):
    user_role = get_user_role()
    return render_template("kelola_rekening.html", user_role=user_role)

@app.route("/kelolaAdmin")
@admin_required
def kelolaAdmin(current_user):
    user_role = get_user_role()
    admins = users_collection.find({'role': 'admin'})
    return render_template("kelola_admin.html", user_role=user_role, admins=admins)

@app.route("/tambahAdmin", methods=['POST'])
@admin_required
def tambahAdmin(current_user):
    email = request.form['email']
    nama = request.form['nama']
    notlp = request.form['notlp']
    alamat = request.form['alamat']
    password = hashlib.sha256('defaultpassword'.encode()).hexdigest()  # Default password for new admin

    if users_collection.find_one({'email': email}):
        flash('Email sudah terdaftar', 'danger')
        return redirect(url_for('kelolaAdmin'))

    new_admin = {
        'email': email,
        'password': password,
        'nama': nama,
        'notlp': notlp,
        'alamat': alamat,
        'fotoprofil': 'static/img/profil/profil.png',  # Default profile picture
        'role': 'admin',
    }
    users_collection.insert_one(new_admin)
    flash('Admin berhasil ditambahkan', 'success')
    return redirect(url_for('kelolaAdmin'))

@app.route("/updateAdmin/<admin_id>", methods=['POST'])
@admin_required
def updateAdmin(current_user, admin_id):
    email = request.form['email']
    nama = request.form['nama']
    notlp = request.form['notlp']
    alamat = request.form['alamat']

    users_collection.update_one(
        {'_id': ObjectId(admin_id)},
        {
            '$set': {
                'email': email,
                'nama': nama,
                'notlp': notlp,
                'alamat': alamat
            }
        }
    )
    flash('Admin berhasil diperbarui', 'success')
    return redirect(url_for('kelolaAdmin'))

@app.route("/hapusAdmin/<admin_id>")
@admin_required
def hapusAdmin(current_user, admin_id):
    users_collection.delete_one({'_id': ObjectId(admin_id)})
    flash('Admin berhasil dihapus', 'success')
    return redirect(url_for('kelolaAdmin'))

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)