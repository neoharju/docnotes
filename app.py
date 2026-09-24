"""Flask app entry point"""

import secrets
import sqlite3
from io import BytesIO
from os import environ

import items
import users
from auth import authenticate_user, check_csrf, require_user_id, safe_redirect_url
from config import Config, DevConfig, TestConfig
from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
)
from flask.typing import ResponseReturnValue
from uploads import UploadError, read_pdf
from werkzeug.utils import secure_filename

app = Flask(__name__)


if environ.get("FLASK_ENV") == "test":
    app.config.from_object(TestConfig)
elif environ.get("FLASK_ENV") == "dev":
    app.config.from_object(DevConfig)
else:
    app.config.from_object(Config)


@app.context_processor
def form_limits() -> dict[str, int | str]:
    return {
        "max_content_length": app.config["MAX_CONTENT_LENGTH"],
        "min_password_length": app.config["MIN_PASSWORD_LENGTH"],
        "max_password_length": app.config["MAX_PASSWORD_LENGTH"],
    }


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

    if (
        not app.config["MIN_PASSWORD_LENGTH"]
        <= len(password_1)
        <= app.config["MAX_PASSWORD_LENGTH"]
    ):
        flash(f"Password must be at least {app.config['MIN_PASSWORD_LENGTH']} characters")
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

    # POST
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    next_page = safe_redirect_url(request.form.get("next_page", "/"))

    user_id = authenticate_user(username, password)
    if user_id is None:
        flash("Wrong username or password")
        return render_template("login.html", next_page=next_page)

    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session["csrf_token"] = secrets.token_hex(32)

    return redirect(next_page)


@app.route("/logout", methods=["POST"])
def logout() -> ResponseReturnValue:
    """Log out the current user"""
    require_user_id()
    check_csrf()
    session.clear()
    return redirect("/")


@app.route("/items")
def item_list() -> ResponseReturnValue:
    """Display all items or a searched item"""
    keyword = request.args.get("search", "").strip()

    if len(keyword) > 200:
        abort(400, "Search query too long")

    if keyword:
        all_items = items.search_items(keyword)
    else:
        all_items = items.get_all_items()

    return render_template("items/list.html", items=all_items, search=keyword)


@app.route("/items/new", methods=["GET", "POST"])
def item_new() -> ResponseReturnValue:
    """User uploads a new PDF"""

    user_id = require_user_id()

    if request.method == "GET":
        return render_template("items/new.html", filled={})

    check_csrf()
    title = request.form.get("title", "").strip()

    if not 1 <= len(title) <= 100:
        flash("Title must be between 1 and 100 characters")
        return render_template("items/new.html", filled={"title": title})

    uploaded_file = request.files.get("pdf")

    if uploaded_file is None:
        flash("No file was selected")
        return render_template(
            "items/new.html",
            filled={"title": title},
        )

    try:
        pdf_data = read_pdf(uploaded_file, current_app.config["MAX_CONTENT_LENGTH"])
    except UploadError as error:
        flash(str(error))
        return render_template("items/new.html", filled={"title": title})

    filename = secure_filename(uploaded_file.filename or "") or "doc.pdf"

    item_id = items.create_item(user_id, title, filename, pdf_data)
    return redirect(f"/items/{item_id}")


@app.route("/items/<int:item_id>")
def item_view(item_id: int) -> ResponseReturnValue:
    """Show an item [user items are not private; they are r not w]"""
    item = items.get_item(item_id)
    if item is None:
        abort(404)

    return render_template("items/view.html", item=item)


@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id: int) -> ResponseReturnValue:
    """User edit own PDF's title or replaces the it"""
    user_id = require_user_id()
    item = items.get_item(item_id)

    if item is None:
        abort(404)

    if item["user_id"] != user_id:
        abort(403)

    if request.method == "GET":
        return render_template("items/edit.html", item=item, filled={"title": item["title"]})

    check_csrf()
    title = request.form.get("title", "").strip()

    if not 1 <= len(title) <= 100:
        flash("Title must be betweeen 1 and 100 characters")
        return render_template("items/edit.html", item=item, filled={"title": title})

    replacement = request.files.get("pdf")
    if replacement is not None and replacement.filename:
        try:
            pdf_data = read_pdf(replacement, current_app.config["MAX_CONTENT_LENGTH"])
        except UploadError as error:
            flash(str(error))
            return render_template("items/edit.html", item=item, filled={"title": title})
        filename = secure_filename(replacement.filename) or item["filename"]
        items.edit_item(item_id, title, filename, pdf_data)
    else:
        items.edit_item(item_id, title)

    return redirect(f"/items/{item_id}")


@app.route("/items/<int:item_id>/delete", methods=["POST"])
def item_delete(item_id: int) -> ResponseReturnValue:
    """User deletes own item"""
    user_id = require_user_id()
    check_csrf()

    item = items.get_item(item_id)

    if item is None:
        abort(404)

    if item["user_id"] != user_id:
        abort(403)

    items.delete_item(item_id)
    return redirect("/items")


@app.route("/items/<int:item_id>/pdf")
def item_pdf(item_id: int) -> ResponseReturnValue:
    row = items.get_item_pdf(item_id)

    if row is None:
        abort(404)

    return send_file(
        BytesIO(row["pdf_data"]),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=row["filename"],
    )


@app.route("/users/<int:user_id>")
def user_profile(user_id: int) -> ResponseReturnValue:
    """Public profile page with user's uploaded items"""
    profile_user = users.get_user(user_id)

    if profile_user is None:
        abort(404)

    user_items = items.get_all_user_items(user_id)
    return render_template("users/profile.html", profile_user=profile_user, items=user_items)
