import os
import sqlite3
from functools import wraps
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "blood_system.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('donor','requester','admin')),
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS donors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        date_of_birth TEXT,
        gender TEXT,
        blood_group TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        address TEXT,
        city TEXT NOT NULL,
        availability_status TEXT NOT NULL DEFAULT 'Available',
        last_donation_date TEXT,
        verification_status TEXT NOT NULL DEFAULT 'Pending'
    );
    CREATE TABLE IF NOT EXISTS blood_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requester_id INTEGER NOT NULL REFERENCES users(id),
        blood_group TEXT NOT NULL,
        required_units INTEGER NOT NULL,
        hospital_name TEXT NOT NULL,
        location TEXT NOT NULL,
        required_date TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'Normal',
        request_status TEXT NOT NULL DEFAULT 'Open',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        message TEXT NOT NULL,
        notification_type TEXT NOT NULL DEFAULT 'Info',
        created_at TEXT NOT NULL,
        read_status INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS donor_searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requester_id INTEGER NOT NULL REFERENCES users(id),
        blood_group TEXT NOT NULL,
        location TEXT,
        search_date TEXT NOT NULL,
        result_count INTEGER NOT NULL
    );
    """)
    # Demo administrator: username admin, password Admin@123
    row = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not row:
        db.execute(
            "INSERT INTO users(username,password_hash,role,status,created_at) VALUES(?,?,?,?,?)",
            ("admin", generate_password_hash("Admin@123"), "admin", "active", datetime.now().isoformat(timespec="seconds"))
        )
    db.commit()
    db.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        if not username or len(password) < 8 or role not in ("donor", "requester"):
            flash("Enter a username, a password with at least 8 characters, and a valid account type.", "danger")
            return redirect(url_for("register"))
        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO users(username,password_hash,role,status,created_at) VALUES(?,?,?,?,?)",
                (username, generate_password_hash(password), role, "active", datetime.now().isoformat(timespec="seconds"))
            )
            user_id = cur.lastrowid
            if role == "donor":
                name = request.form.get("name", "").strip()
                blood_group = request.form.get("blood_group", "")
                phone = request.form.get("phone", "").strip()
                city = request.form.get("city", "").strip()
                if not all([name, blood_group in BLOOD_GROUPS, phone, city]):
                    db.rollback()
                    flash("Donor name, valid blood group, phone, and city are required.", "danger")
                    return redirect(url_for("register"))
                db.execute("""INSERT INTO donors
                    (user_id,name,date_of_birth,gender,blood_group,phone,email,address,city,availability_status,verification_status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (user_id, name, request.form.get("date_of_birth") or None,
                     request.form.get("gender") or None, blood_group, phone,
                     request.form.get("email", "").strip(), request.form.get("address", "").strip(),
                     city, "Available", "Pending"))
            db.commit()
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            db.rollback()
            flash("That username is already registered.", "danger")
    return render_template("register.html", blood_groups=BLOOD_GROUPS)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username=? AND status='active'", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    role = session["role"]
    if role == "donor":
        donor = db.execute("SELECT * FROM donors WHERE user_id=?", (session["user_id"],)).fetchone()
        notes = db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 5", (session["user_id"],)).fetchall()
        return render_template("dashboard.html", donor=donor, notifications=notes)
    if role == "requester":
        requests = db.execute("SELECT * FROM blood_requests WHERE requester_id=? ORDER BY id DESC", (session["user_id"],)).fetchall()
        return render_template("dashboard.html", requests=requests)
    stats = {
        "donors": db.execute("SELECT COUNT(*) FROM donors").fetchone()[0],
        "pending": db.execute("SELECT COUNT(*) FROM donors WHERE verification_status='Pending'").fetchone()[0],
        "requests": db.execute("SELECT COUNT(*) FROM blood_requests").fetchone()[0]
    }
    pending_donors = db.execute("""SELECT donors.*, users.username FROM donors
        JOIN users ON users.id=donors.user_id WHERE donors.verification_status='Pending'
        ORDER BY donors.id DESC""").fetchall()
    return render_template("dashboard.html", stats=stats, pending_donors=pending_donors)

@app.route("/profile", methods=["GET", "POST"])
@role_required("donor")
def profile():
    db = get_db()
    donor = db.execute("SELECT * FROM donors WHERE user_id=?", (session["user_id"],)).fetchone()
    if not donor:
        flash("Donor profile was not found.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        required = [request.form.get("name", "").strip(), request.form.get("phone", "").strip(),
                    request.form.get("city", "").strip(), request.form.get("blood_group", "")]
        if not all(required) or required[3] not in BLOOD_GROUPS:
            flash("Please complete all required fields.", "danger")
        else:
            db.execute("""UPDATE donors SET name=?,date_of_birth=?,gender=?,blood_group=?,phone=?,
                email=?,address=?,city=?,availability_status=?,last_donation_date=? WHERE user_id=?""",
                (required[0], request.form.get("date_of_birth") or None, request.form.get("gender") or None,
                 required[3], required[1], request.form.get("email", "").strip(),
                 request.form.get("address", "").strip(), required[2],
                 request.form.get("availability_status", "Available"),
                 request.form.get("last_donation_date") or None, session["user_id"]))
            db.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
    donor = db.execute("SELECT * FROM donors WHERE user_id=?", (session["user_id"],)).fetchone()
    return render_template("profile.html", donor=donor, blood_groups=BLOOD_GROUPS)

@app.route("/search", methods=["GET", "POST"])
@role_required("requester", "admin", "coordinator")
def search_donors():
    results = []
    blood_group = request.values.get("blood_group", "")
    city = request.values.get("city", "").strip()
    availability = request.values.get("availability", "")
    if request.method == "POST" or any([blood_group, city, availability]):
        query = """SELECT id,name,blood_group,phone,email,city,availability_status,verification_status
                   FROM donors WHERE verification_status='Verified'"""
        params = []
        if blood_group in BLOOD_GROUPS:
            query += " AND blood_group=?"; params.append(blood_group)
        if city:
            query += " AND city LIKE ?"; params.append(f"%{city}%")
        if availability in ("Available", "Unavailable"):
            query += " AND availability_status=?"; params.append(availability)
        query += " ORDER BY name"
        results = get_db().execute(query, params).fetchall()
        if session.get("role") == "requester":
            get_db().execute("""INSERT INTO donor_searches(requester_id,blood_group,location,search_date,result_count)
                VALUES(?,?,?,?,?)""", (session["user_id"], blood_group, city, datetime.now().isoformat(timespec="seconds"), len(results)))
            get_db().commit()
    return render_template("search.html", results=results, blood_groups=BLOOD_GROUPS,
                           selected_group=blood_group, city=city, availability=availability)

@app.route("/requests/new", methods=["GET", "POST"])
@role_required("requester")
def new_request():
    if request.method == "POST":
        group = request.form.get("blood_group", "")
        units = request.form.get("required_units", type=int)
        hospital = request.form.get("hospital_name", "").strip()
        location = request.form.get("location", "").strip()
        required_date = request.form.get("required_date", "")
        priority = request.form.get("priority", "Normal")
        if group not in BLOOD_GROUPS or not units or units < 1 or not hospital or not location or not required_date:
            flash("Please enter valid request details.", "danger")
        else:
            db = get_db()
            db.execute("""INSERT INTO blood_requests(requester_id,blood_group,required_units,hospital_name,
                location,required_date,priority,request_status,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                (session["user_id"], group, units, hospital, location, required_date, priority, "Open",
                 datetime.now().isoformat(timespec="seconds")))
            db.commit()
            flash("Blood request submitted.", "success")
            return redirect(url_for("dashboard"))
    return render_template("request_form.html", blood_groups=BLOOD_GROUPS)

@app.route("/admin/donors/<int:donor_id>/<action>", methods=["POST"])
@role_required("admin")
def verify_donor(donor_id, action):
    if action not in ("verify", "reject"):
        flash("Invalid action.", "danger")
    else:
        status = "Verified" if action == "verify" else "Rejected"
        db = get_db()
        donor = db.execute("SELECT * FROM donors WHERE id=?", (donor_id,)).fetchone()
        if donor:
            db.execute("UPDATE donors SET verification_status=? WHERE id=?", (status, donor_id))
            db.execute("INSERT INTO notifications(user_id,message,notification_type,created_at) VALUES(?,?,?,?)",
                       (donor["user_id"], f"Your donor profile verification status is {status}.",
                        "Verification", datetime.now().isoformat(timespec="seconds")))
            db.commit()
            flash(f"Donor {status.lower()}.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/requests")
@role_required("admin")
def admin_requests():
    rows = get_db().execute("""SELECT blood_requests.*, users.username FROM blood_requests
        JOIN users ON users.id=blood_requests.requester_id ORDER BY blood_requests.id DESC""").fetchall()
    return render_template("admin_requests.html", requests=rows)

@app.route("/admin/requests/<int:request_id>", methods=["POST"])
@role_required("admin")
def update_request(request_id):
    status = request.form.get("request_status")
    if status not in ("Open", "In Progress", "Fulfilled", "Cancelled"):
        flash("Invalid request status.", "danger")
    else:
        db = get_db()
        db.execute("UPDATE blood_requests SET request_status=? WHERE id=?", (status, request_id))
        db.commit()
        flash("Request status updated.", "success")
    return redirect(url_for("admin_requests"))

@app.route("/notifications")
@login_required
def notifications():
    rows = get_db().execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC",
                            (session["user_id"],)).fetchall()
    get_db().execute("UPDATE notifications SET read_status=1 WHERE user_id=?", (session["user_id"],))
    get_db().commit()
    return render_template("notifications.html", notifications=rows)

@app.errorhandler(404)
def not_found(error):
    return render_template("message.html", title="Page not found", message="The page you requested does not exist."), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
