import os
import sqlite3
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {"gif", "jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-this-secret"),
        DATABASE=os.environ.get("DATABASE", str(BASE_DIR / "instance" / "foodshare.sqlite")),
        UPLOAD_FOLDER=os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "static" / "uploads")),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_SIZE,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    @app.before_request
    def open_db():
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row

    @app.teardown_request
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    init_db(app)

    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please sign in first.", "error")
                return redirect(url_for("signin"))
            return view(*args, **kwargs)

        return wrapped_view

    @app.route("/", methods=["GET", "POST"])
    def signin():
        if request.method == "POST":
            email = clean_text(request.form.get("email"))
            password = request.form.get("password", "")
            user = get_user_by_email(email)

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("home"))

            flash("Invalid email or password.", "error")

        return render_template("base.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("signin"))

    @app.route("/home")
    @login_required
    def home():
        return render_template("index.html")

    @app.route("/donate", methods=["GET", "POST"])
    @login_required
    def donate():
        if request.method == "POST":
            data, errors = validate_donation(request.form)
            filename, upload_error = save_upload(request.files.get("image-upload"))
            if upload_error:
                errors.append(upload_error)

            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template("donate.html", donations=get_donations(), form=request.form), 400

            g.db.execute(
                """
                INSERT INTO donations
                    (name, location, contact, food_type, quantity, donation_date, expiry_date, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"],
                    data["location"],
                    data["contact"],
                    data["food_type"],
                    data["quantity"],
                    data["donation_date"],
                    data["expiry_date"],
                    filename,
                ),
            )
            g.db.commit()
            flash("Donation submitted.", "success")
            return redirect(url_for("donate"))

        return render_template("donate.html", donations=get_donations())

    @app.route("/request", methods=["GET", "POST"])
    @login_required
    def request_page():
        if request.method == "POST":
            data, errors = validate_food_request(request.form)
            filename, upload_error = save_upload(request.files.get("image-upload"))
            if upload_error:
                errors.append(upload_error)

            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template("request.html", requests=get_requests(), form=request.form), 400

            g.db.execute(
                """
                INSERT INTO food_requests
                    (name, contact, type_request, quantity, urgency, special, image)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"],
                    data["contact"],
                    data["type_request"],
                    data["quantity"],
                    data["urgency"],
                    data["special"],
                    filename,
                ),
            )
            g.db.commit()
            flash("Request submitted.", "success")
            return redirect(url_for("request_page"))

        return render_template("request.html", requests=get_requests())

    @app.route("/listings")
    @login_required
    def listings():
        return render_template("listing.html", donations=get_donations(), requests=get_requests())

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            data, errors = validate_profile(request.form)
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_profile(data), 400

            update_values = [data["name"], data["role"], data["contact"], data["bio"]]
            sql = "UPDATE users SET name = ?, role = ?, contact = ?, bio = ?"
            if data["password"]:
                sql += ", password_hash = ?"
                update_values.append(generate_password_hash(data["password"]))
            sql += " WHERE id = ?"
            update_values.append(session["user_id"])

            g.db.execute(sql, update_values)
            g.db.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))

        user = dict(get_current_user())
        user["password"] = ""
        return render_profile(user)

    return app


def init_db(app):
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT '',
                contact TEXT NOT NULL DEFAULT '',
                bio TEXT NOT NULL DEFAULT 'Some short biography here...'
            );

            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                contact TEXT NOT NULL,
                food_type TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                donation_date TEXT NOT NULL,
                expiry_date TEXT NOT NULL DEFAULT '',
                image TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS food_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                type_request TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                urgency TEXT NOT NULL DEFAULT '',
                special TEXT NOT NULL DEFAULT '',
                image TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        email = os.environ.get("DEFAULT_USER_EMAIL", "user@example.com")
        password = os.environ.get("DEFAULT_USER_PASSWORD", "mypassword")
        existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user is None:
            db.execute(
                """
                INSERT INTO users (email, password_hash, name, role, contact, bio)
                VALUES (?, ?, '', '', '', 'Some short biography here...')
                """,
                (email, generate_password_hash(password)),
            )
        db.commit()
        db.close()


def clean_text(value, max_length=255):
    return (value or "").strip()[:max_length]


def positive_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def validate_donation(form):
    data = {
        "name": clean_text(form.get("donor-name")),
        "location": clean_text(form.get("location")),
        "contact": clean_text(form.get("contact")),
        "food_type": clean_text(form.get("food-type")),
        "quantity": positive_int(form.get("quantity")),
        "donation_date": clean_text(form.get("donation-date")),
        "expiry_date": clean_text(form.get("expiry-date")),
    }
    errors = required_errors(data, ["name", "location", "contact", "food_type", "donation_date"])
    if data["quantity"] is None:
        errors.append("Quantity must be a positive number.")
    return data, errors


def validate_food_request(form):
    data = {
        "name": clean_text(form.get("requester-name")),
        "contact": clean_text(form.get("contact")),
        "type_request": clean_text(form.get("type-request")),
        "quantity": positive_int(form.get("quantity")),
        "urgency": clean_text(form.get("urgency")),
        "special": clean_text(form.get("special"), 1000),
    }
    errors = required_errors(data, ["name", "contact", "type_request"])
    if data["quantity"] is None:
        errors.append("Quantity must be a positive number.")
    return data, errors


def validate_profile(form):
    data = {
        "name": clean_text(form.get("user-name")),
        "role": clean_text(form.get("role")),
        "contact": clean_text(form.get("contact")),
        "password": request.form.get("password", ""),
        "bio": clean_text(form.get("bio"), 1000),
    }
    errors = []
    if data["password"] and len(data["password"]) < 8:
        errors.append("Password must be at least 8 characters.")
    return data, errors


def required_errors(data, fields):
    return [f"{field.replace('_', ' ').title()} is required." for field in fields if not data[field]]


def save_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return "", None

    original_name = secure_filename(file_storage.filename)
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        return "", "Only gif, jpg, jpeg, png, and webp images are allowed."

    filename = f"{uuid4().hex}.{extension}"
    file_storage.save(Path(current_app.config["UPLOAD_FOLDER"]) / filename)
    return filename, None


def get_user_by_email(email):
    return g.db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_current_user():
    return g.db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()


def get_donations():
    rows = g.db.execute("SELECT * FROM donations ORDER BY created_at DESC, id DESC").fetchall()
    return [dict(row) for row in rows]


def get_requests():
    rows = g.db.execute("SELECT * FROM food_requests ORDER BY created_at DESC, id DESC").fetchall()
    return [dict(row) for row in rows]


def render_profile(profile_info):
    donations = get_donations()
    requests_db = get_requests()
    total_donated = sum(int(d["quantity"]) for d in donations)
    total_requested = sum(int(r["quantity"]) for r in requests_db)
    return render_template(
        "profile.html",
        profile=profile_info,
        donations=donations,
        requests=requests_db,
        total_donated=total_donated,
        total_requested=total_requested,
    )


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
