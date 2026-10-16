"""Flask app entry point"""

import math
import secrets
import sqlite3
from io import BytesIO
from os import environ

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
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.utils import secure_filename

import comments
import items
import users
from auth import (
    authenticate_user,
    check_csrf,
    require_owner,
    require_user_id,
    safe_redirect_url,
)
from config import Config, DevConfig, TestConfig
from uploads import UploadError, read_pdf

app = Flask(__name__)


if environ.get("FLASK_ENV") == "test":
    app.config.from_object(TestConfig)
elif environ.get("FLASK_ENV") == "dev":
    app.config.from_object(DevConfig)
else:
    app.config.from_object(Config)


@app.context_processor
def form_limits() -> dict[str, int]:
    """Size limits for the form templates"""
    return {
        "max_pdf_mb": app.config["MAX_PDF_SIZE"] // (1024 * 1024),
        "min_password_length": app.config["MIN_PASSWORD_LENGTH"],
        "max_password_length": app.config["MAX_PASSWORD_LENGTH"],
        "min_username_length": app.config["MIN_USERNAME_LENGTH"],
        "max_username_length": app.config["MAX_USERNAME_LENGTH"],
    }


_lim = form_limits()


@app.context_processor
def form_classes() -> dict[str, object]:
    """The selectable classes for the forms"""

    if request.endpoint in ("item_new", "item_edit"):
        return {"all_classes": items.get_all_classes()}

    return {}


def _page(item_count: int) -> tuple[int, int]:
    """The page number in ?page= in url"""
    page_count = max(1, math.ceil(item_count / items.PAGE_SIZE))
    page = request.args.get("page", 1, type=int)
    return min(max(page, 1), page_count), page_count


def _selected_class_ids() -> list[int]:
    """IDs of the classes"""

    valid_ids = {row["id"] for rows in items.get_all_classes().values() for row in rows}
    class_ids: set[int] = set()

    for value in request.form.getlist("classes"):
        if not value.isdecimal() or int(value) not in valid_ids:
            abort(400, "Unknown classification")
        class_ids.add(int(value))

    return sorted(class_ids)


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(error: RequestEntityTooLarge) -> ResponseReturnValue:
    """MAX_PDF_SIZE is the largest possible upload, if it is exceeded
    send user back to upload form with message
    """

    if request.endpoint not in ("item_new", "item_edit"):
        return http_error(error)

    flash(f"Upload limit is for PDFs {_lim['max_pdf_mb']} MB")

    return redirect(request.path, 303)


@app.errorhandler(HTTPException)
def http_error(error: HTTPException) -> ResponseReturnValue:
    """show HTTP errors inside the layout"""
    response = error.get_response()
    response.set_data(render_template("error.html", error=error))
    return response


@app.route("/")
def index() -> str:
    """Home page with the three latest PDFs"""
    return render_template("index.html", items=items.get_items()[:3])


# helper function to start session
def _start_session(user_id: int, username: str) -> None:
    """Log in the user with a new session"""
    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session["csrf_token"] = secrets.token_hex(64)  # was 32


@app.route("/register", methods=["GET", "POST"])
def register() -> ResponseReturnValue:
    """Register new user and log them in"""
    if request.method == "GET":
        next_page = safe_redirect_url(request.args.get("next", "/"))
        return render_template("register.html", next_page=next_page, filled={})

    username = request.form.get("username", "").strip()
    password_1 = request.form.get("password_1", "")
    password_2 = request.form.get("password_2", "")
    next_page = safe_redirect_url(request.form.get("next_page", "/"))

    # Helper function for repetetive code
    def retry(message: str) -> str:
        flash(message)
        return render_template(
            "register.html", next_page=next_page, filled={"username": username}
        )

    if not _lim["min_username_length"] <= len(username) <= _lim["max_username_length"]:
        return retry("Username should be between 2 and 20 characters")

    if (
        not _lim["min_password_length"]
        <= len(password_1)
        <= _lim["max_password_length"]
    ):
        return retry(
            f"Password must be at least {_lim['min_password_length']} characters"
        )

    if password_1 != password_2:
        return retry("The passwords do not match!")

    try:
        user_id = users.create_user(username, password_1)
    except sqlite3.IntegrityError:
        return retry("Username is unavailable")

    _start_session(user_id, username)
    flash(f"Welcome, {username}! Thanks for joining us.")
    return redirect(next_page)


@app.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    """Authenticate user and create session"""
    if request.method == "GET":
        next_page = safe_redirect_url(request.args.get("next", "/"))
        return render_template("login.html", next_page=next_page, filled={})

    # POST
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    next_page = safe_redirect_url(request.form.get("next_page", "/"))

    check_length = (
        len(username) > _lim["max_username_length"]
        or len(password) > _lim["max_password_length"]
    )
    user_id = None if check_length else authenticate_user(username, password)
    if user_id is None:
        flash("Wrong username or password")
        return render_template(
            "login.html", next_page=next_page, filled={"username": username}
        )

    _start_session(user_id, username)

    return redirect(next_page)


@app.route("/logout", methods=["POST"])
def logout() -> ResponseReturnValue:
    """Log out the current user"""
    if "user_id" in session:
        check_csrf()
        session.clear()
    return redirect("/")


@app.route("/items")
def item_list() -> ResponseReturnValue:
    """Display all items, search results or items with keyword"""
    search = request.args.get("search", "").strip()
    keyword = items.normalize_keyword(request.args.get("keyword", ""))
    sort = request.args.get("sort", "recent")
    if sort not in items.SORT_ORDERS:
        sort = "recent"

    if len(search) > 200 or len(keyword) > items.MAX_KEYWORD_LENGTH:
        abort(400, "Search query too long")

    page, page_count = _page(items.count_items(search, keyword))
    page_items = items.get_items(search, keyword, sort=sort, page=page)

    return render_template(
        "items/list.html",
        items=page_items,
        search=search,
        keyword=keyword,
        sort=sort,
        page=page,
        page_count=page_count,
    )


@app.route("/items/new", methods=["GET", "POST"])
def item_new() -> ResponseReturnValue:
    """User uploads a new PDF"""

    user_id = require_user_id()

    if request.method == "GET":
        return render_template("items/new.html", filled={})

    check_csrf()
    title = request.form.get("title", "").strip()
    keyword_text = request.form.get("keywords", "")
    class_ids = _selected_class_ids()
    filled = {"title": title, "keywords": keyword_text, "classes": class_ids}

    if not 1 <= len(title) <= 100:
        flash("Title must be between 1 and 100 characters")
        return render_template("items/new.html", filled=filled)

    try:
        keywords = items.parse_keywords(keyword_text)
    except ValueError as error:
        flash(str(error))
        return render_template("items/new.html", filled=filled)

    uploaded_file = request.files.get("pdf")

    if uploaded_file is None:
        flash("No file was selected")
        return render_template("items/new.html", filled=filled)

    try:
        pdf_data = read_pdf(uploaded_file, current_app.config["MAX_PDF_SIZE"])
    except UploadError as error:
        flash(str(error))
        return render_template("items/new.html", filled=filled)

    filename = secure_filename(uploaded_file.filename or "") or "doc.pdf"
    pdf = items.PdfFile(filename, pdf_data)

    item_id = items.create_item(
        user_id, title, pdf, keywords=keywords, class_ids=class_ids
    )
    return redirect(f"/items/{item_id}")


@app.route("/items/<int:item_id>")
def item_view(item_id: int) -> ResponseReturnValue:
    """Show an item and its comments [user items are not private]"""
    item = items.get_item(item_id)
    if item is None:
        abort(404)

    item_comments = comments.get_comments(item_id)
    item_classes = items.get_item_classes(item_id)
    return render_template(
        "items/view.html", item=item, comments=item_comments, classes=item_classes
    )


@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id: int) -> ResponseReturnValue:
    """User edit own PDF's title or replaces the it"""
    user_id = require_user_id()

    item = require_owner(items.get_item(item_id), user_id)

    if request.method == "GET":
        filled = {
            "title": item["title"],
            "keywords": items.keywords_text(item["keywords"]),
            "classes": items.get_item_class_ids(item_id),
        }
        return render_template("items/edit.html", item=item, filled=filled)

    check_csrf()
    title = request.form.get("title", "").strip()
    keyword_text = request.form.get("keywords", "")
    class_ids = _selected_class_ids()
    filled = {"title": title, "keywords": keyword_text, "classes": class_ids}

    if not 1 <= len(title) <= 100:
        flash("Title must be between 1 and 100 characters")
        return render_template("items/edit.html", item=item, filled=filled)

    try:
        keywords = items.parse_keywords(keyword_text)
    except ValueError as error:
        flash(str(error))
        return render_template("items/edit.html", item=item, filled=filled)

    pdf: items.PdfFile | None = None
    replacement = request.files.get("pdf")
    if replacement is not None and replacement.filename:
        try:
            pdf_data = read_pdf(replacement, current_app.config["MAX_PDF_SIZE"])
        except UploadError as error:
            flash(str(error))
            return render_template("items/edit.html", item=item, filled=filled)
        filename = secure_filename(replacement.filename) or item["filename"]
        pdf = items.PdfFile(filename, pdf_data)

    items.edit_item(item_id, title, pdf, keywords=keywords, class_ids=class_ids)
    return redirect(f"/items/{item_id}")


@app.route("/items/<int:item_id>/delete", methods=["POST"])
def item_delete(item_id: int) -> ResponseReturnValue:
    """User deletes own item"""
    user_id = require_user_id()
    check_csrf()
    require_owner(items.get_item(item_id), user_id)

    items.delete_item(item_id)
    return redirect("/items")


@app.route("/items/<int:item_id>/pdf")
def item_pdf(item_id: int) -> ResponseReturnValue:
    """Send the PDF file to the browser"""
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
    """Public profile page with user's statistics and uploaded items"""
    profile_user = users.get_user(user_id)

    if profile_user is None:
        abort(404)

    stats = users.get_stats(user_id)
    page, page_count = _page(stats["pdfs"])
    user_items = items.get_items(user_id=user_id, page=page)
    return render_template(
        "users/profile.html",
        profile_user=profile_user,
        items=user_items,
        stats=stats,
        page=page,
        page_count=page_count,
    )


@app.route("/items/<int:item_id>/comments", methods=["POST"])
def comment_new(item_id: int) -> ResponseReturnValue:
    """Add a comment to an item. Requires login."""
    user_id = require_user_id()
    check_csrf()

    if items.get_item(item_id) is None:
        abort(404)

    content = request.form.get("content", "").strip()
    if not 1 <= len(content) <= 2000:
        flash("Comment must be between 1 and 2000 characters")
        return redirect(f"/items/{item_id}")

    comments.create_comment(item_id, user_id, content)
    return redirect(f"/items/{item_id}")


@app.route("/comments/<int:comment_id>/delete", methods=["POST"])
def comment_delete(comment_id: int) -> ResponseReturnValue:
    """Delete a comment. Only the comment's author may delete it."""
    user_id = require_user_id()
    check_csrf()

    comment = require_owner(comments.get_comment(comment_id), user_id)

    comments.delete_comment(comment_id)
    return redirect(f"/items/{comment['item_id']}")
