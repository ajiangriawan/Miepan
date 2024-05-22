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


app = Flask(__name__)

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


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)