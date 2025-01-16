import folium
from json import JSONEncoder
from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import numpy as np
import statistics
from sklearn.cluster import KMeans
import io
import re
from decimal import Decimal
from pyproj import Proj
from flask import Flask,render_template, request, redirect, session, url_for, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import os, sys, math, stat, json , jinja2
from os import listdir, system
from markupsafe import escape
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from urllib.parse import urlparse, urljoin
from werkzeug.security import generate_password_hash, check_password_hash
import Normalised, ElectorWalks
from werkzeug.utils import secure_filename

Env1 = sys.base_prefix

app = Flask(__name__)
sys.path.append(r'/Users/newbrie/Documents/ReformUK/GitHub/Electtrek')
# Configure Alchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/newbrie/Documents/ReformUK/GitHub/Electtrek/trekusers.db'
app.config['SECRET_KEY'] = 'rosebutt'
app.config['USE_SESSION_FOR_NEXT'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/Users/newbrie/Sites'
app.config['APPLICATION_ROOT'] = '/Users/newbrie/Documents/ReformUK/GitHub/Electtrek'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = '<h1>login</h1>'
login_manager.login_message = "<h1>You really need to login!!</h1>"
login_manager.refresh_view = "<h1>Login</h1>"
login_manager.needs_refresh_message = "<h1>You really need to re-login to access this page</h1>"
allelectors = []
mapfile = ""
testdir = "/Users/newbrie/Documents/ReformUK/ElectoralRegisters/Test"
staticdir = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek"
workdir = "/Users/newbrie/Sites"
templdir = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/templates"
bounddir = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/Boundaries/"
os.chdir(staticdir)
# Database Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self,password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash, password)


@app.route("/")
def home():
    if "username" in session:
        return redirect (url_for('dashboard'))
    return render_template("index.html")


if __name__ in '__main__':
    with app.app_context():
        print("__________Directory0", os.getcwd())
        db.create_all()
        app.run(debug=True)

# Add children to root
