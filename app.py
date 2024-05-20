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




if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)