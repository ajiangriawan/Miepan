from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import os
from os.path import join, dirname
from dotenv import load_dotenv
import random
from datetime import datetime, timedelta

app = Flask(__name__)

def generate_fake_sales_data(num_days):
    sales_data = []
    base_date = datetime.now()
    for i in range(num_days):
        date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
        sales = random.randint(50, 150)
        sales_data.append({"date": date, "sales": sales})
    return sales_data

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/regis")
def regis():
    return render_template("register.html")

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
def profil():
    return render_template("profil.html")

@app.route("/editProfil")
def editProfil():
    return render_template("edit_profil.html")

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