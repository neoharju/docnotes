"""Flask app entry point"""

import os
import secrets
import sqlite3

import users
from auth import authenticate_user, require_user_id, safe_redirect_url
from config import Config, DevConfig, TestConfig
from flask import Flask, flash, redirect, render_template, request, session
from flask.typing import ResponseReturnValue

app = Flask(__name__)


if os.environ.get("FLASK_ENV") == "test":
    app.config.from_object(TestConfig)
elif os.environ.get("FLASK_ENV") == "dev":
    app.config.from_object(DevConfig)
else:
    app.config.from_object(Config)


@app.route("/")
def index() -> str:
    """Render the home page"""
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register() -> ResponseReturnValue:
    """Register new user"""
    if request.method == "GET":
        return render_template("register.html", filled={})

    username = request.form.get("username", "").strip()
    password_1 = request.form.get("password_1", "")
    password_2 = request.form.get("password_2", "")

    if not 2 <= len(username) <= 20:
        flash("Username should be between 2 and 20 characters")
        return render_template("register.html", filled={"username": username})

    if password_1 != password_2:
        flash("The passwords do not match!")
        return render_template("register.html", filled={"username": username})

    try:
        users.create_user(username, password_1)
    except sqlite3.IntegrityError:
        flash("Username is unavailable")
        return render_template("register.html", filled={"username": username})

    flash("Account created. You may now login")
    return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    """Authenticate user and create session"""
    if request.method == "GET":
        next_page = safe_redirect_url(request.args.get("next", "/"))
        return render_template("login.html", next_page=next_page)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    next_page = request.form.get("next_page", "/")

    user_id = authenticate_user(username, password)
    if user_id is None:
        flash("Wrong username or password")
        return render_template("login.html", next_page=next_page)

    session.clear()
    session["user_id"] = user_id
    session["csrf_token"] = secrets.token_hex(32)

    return redirect(next_page)


@app.route("/logout", methods=["POST"])
def logout() -> ResponseReturnValue:
    """Log out the current user"""
    require_user_id()
    session.clear()
    return redirect("/")
