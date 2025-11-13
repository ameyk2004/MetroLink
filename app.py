# app.py (FINAL FIXED VERSION)
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from datetime import datetime, date, time, timedelta
import qrcode, io, base64

app = Flask(__name__)
app.config["SECRET_KEY"] = "simple123"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Amey1234",
    "database": "metro_ticketing"
}

# ------------ TIME HANDLING FIX ------------
def mysql_time_to_time(t):
    """Convert MySQL TIME (timedelta or time) → datetime.time safely."""
    if isinstance(t, time):
        return t

    if isinstance(t, timedelta):
        total = int(t.total_seconds())
        hours = (total // 3600) % 24
        minutes = (total % 3600) // 60
        seconds = total % 60
        return time(hours, minutes, seconds)

    return time(0, 0, 0)

def format_time(t):
    """Convert MySQL TIME to 12-hour formatted time string."""
    tt = mysql_time_to_time(t)
    return tt.strftime("%I:%M %p")


def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

# -------- LOGIN MANAGER --------
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, row):
        self.user_id = row["user_id"]
        self.email = row.get("email")
        self.name = row.get("name")
        self.role_id = row.get("role_id", 2)
        self.role_name = row.get("role_name", "user")

    @property
    def id(self):
        return self.user_id

@login_manager.user_loader
def load_user(user_id):
    try:
        uid = int(user_id)
    except:
        return None
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT u.*, r.role_name 
                   FROM users u JOIN roles r ON u.role_id=r.role_id 
                   WHERE u.user_id=%s""", (uid,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return User(row) if row else None

# -------- SIMPLE HOME --------
@app.route('/')
def index():
    return render_template('index.html')

# -------- REGISTER --------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['name'].strip()
        email=request.form['email'].strip()
        password=request.form['password']

        conn=get_conn(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s",(email,))
        if cur.fetchone():
            cur.close(); conn.close()
            flash("Email already exists","danger")
            return redirect(url_for('register'))

        pwd_hash=generate_password_hash(password)
        cur2=conn.cursor()
        cur2.execute("INSERT INTO users(name,email,role_id,password_hash) VALUES(%s,%s,2,%s)",
                    (name,email,pwd_hash))
        conn.commit()
        cur2.close(); cur.close(); conn.close()
        flash("Registered! Login now","success")
        return redirect(url_for('login'))

    return render_template("register.html")

# -------- LOGIN --------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email'].strip()
        password=request.form['password']
        conn=get_conn(); cur=conn.cursor(dictionary=True)
        cur.execute("""SELECT u.*, r.role_name 
                       FROM users u LEFT JOIN roles r ON u.role_id=r.role_id 
                       WHERE u.email=%s""",(email,))
        user=cur.fetchone()
        cur.close(); conn.close()
        if not user or not user.get('password_hash') or not check_password_hash(user['password_hash'], password):
            flash("Invalid credentials","danger")
            return redirect(url_for('login'))
        login_user(User(user))
        return redirect(url_for('dashboard'))
    return render_template("login.html")

# -------- STOPS API --------
@app.route('/stops/<int:line_id>')
@login_required
def stops_for_line(line_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT stop_id, stop_name, stop_order FROM stops WHERE line_id=%s ORDER BY stop_order", (line_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(rows)

# -------- DASHBOARD --------
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    # Load all metro lines
    cur.execute("SELECT line_id, line_name FROM metro_lines ORDER BY line_id")
    lines = cur.fetchall()

    # Load user's passes
    cur.execute("""
        SELECT 
            p.pass_id, 
            p.line_id, 
            p.balance, 
            p.start_date, 
            p.end_date, 
            m.line_name
        FROM passes p
        JOIN metro_lines m ON p.line_id = m.line_id
        WHERE p.user_id = %s
        ORDER BY p.pass_id
    """, (current_user.user_id,))
    passes = cur.fetchall()

    # Load tickets WITH stop names
    cur.execute("""
        SELECT 
            t.ticket_id,
            t.travel_date,
            t.fare,
            t.use_pass,
            t.is_used,
            s1.stop_name AS from_name,
            s2.stop_name AS to_name
        FROM tickets t
        JOIN stops s1 ON t.from_stop = s1.stop_id
        JOIN stops s2 ON t.to_stop   = s2.stop_id
        WHERE t.user_id = %s
        ORDER BY t.travel_date DESC
    """, (current_user.user_id,))
    tickets = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'dashboard.html',
        lines=lines,
        passes=passes,
        tickets=tickets
    )

# -------- BUY PASS --------
@app.route('/buy_pass', methods=['GET','POST'])
@login_required
def buy_pass():
    conn=get_conn(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT line_id, line_name FROM metro_lines ORDER BY line_id")
    lines=cur.fetchall()

    if request.method=='POST':
        line_id=request.form['line_id']
        amount=float(request.form['amount'])

        start_date = date.fromisoformat(request.form['start_date'])
        end_date=start_date + timedelta(days=30)

        cur2=conn.cursor()
        cur2.execute("INSERT INTO passes(user_id,line_id,balance,start_date,end_date) VALUES(%s,%s,%s,%s,%s)",
                     (current_user.user_id,line_id,amount,start_date,end_date))
        conn.commit()
        cur2.close(); cur.close(); conn.close()
        flash("Pass purchased","success")
        return redirect(url_for('dashboard'))

    cur.close(); conn.close()
    return render_template("buy_pass.html", lines=lines)

# -------- FARE --------
def calculate_fare(user_id, s1, s2):
    conn=get_conn(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT stop_order FROM stops WHERE stop_id=%s",(s1,))
    o1=cur.fetchone()
    cur.execute("SELECT stop_order FROM stops WHERE stop_id=%s",(s2,))
    o2=cur.fetchone()
    total=abs(o1['stop_order']-o2['stop_order'])
    today=date.today()
    cur.execute("""SELECT COUNT(*) as c FROM passes 
                   WHERE user_id=%s AND start_date<=%s AND end_date>=%s""",
                (user_id,today,today))
    has=cur.fetchone()['c']
    cur.close(); conn.close()
    return total * (15 if has>0 else 20)

# -------- BOOK TICKET --------
@app.route('/book_ticket', methods=['GET', 'POST'])
@login_required
def book_ticket():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT line_id, line_name FROM metro_lines ORDER BY line_id")
    lines = cur.fetchall()

    if request.method == 'POST':
        line_id = int(request.form['line_id'])
        from_stop = int(request.form['from_stop'])
        to_stop = int(request.form['to_stop'])
        schedule_id = int(request.form['schedule_id'])

        cur.execute("SELECT line_id, stop_order FROM stops WHERE stop_id=%s", (from_stop,))
        s1 = cur.fetchone()
        cur.execute("SELECT line_id, stop_order FROM stops WHERE stop_id=%s", (to_stop,))
        s2 = cur.fetchone()

        direction = 'UP' if s1['stop_order'] < s2['stop_order'] else 'DOWN'

        cur.execute("""
            SELECT * FROM train_schedule
            WHERE schedule_id=%s AND line_id=%s AND stop_id=%s AND direction=%s
        """, (schedule_id, line_id, from_stop, direction))
        train = cur.fetchone()

        travel_time = mysql_time_to_time(train['departure_time'])

        fare = calculate_fare(current_user.user_id, from_stop, to_stop)

        today = date.today()
        travel_dt = datetime.combine(today, travel_time)

        # Pass handling
        cur.execute("""
            SELECT pass_id, balance FROM passes
            WHERE user_id=%s AND line_id=%s AND start_date<=%s AND end_date>=%s
            ORDER BY start_date DESC LIMIT 1
        """, (current_user.user_id, line_id, today, today))
        p = cur.fetchone()

        use_pass = 'N'
        if p and float(p['balance']) >= float(fare):
            use_pass = 'Y'
            newbal = float(p['balance']) - float(fare)
            cur.execute("UPDATE passes SET balance=%s WHERE pass_id=%s", (newbal, p['pass_id']))

        cur.execute("""
            INSERT INTO tickets(user_id, line_id, from_stop, to_stop, travel_date, fare, use_pass, is_used)
            VALUES(%s, %s, %s, %s, %s, %s, %s, 0)
        """, (
            current_user.user_id,
            line_id,
            from_stop,
            to_stop,
            travel_dt,
            fare,
            use_pass
        ))

        ticket_id = cur.lastrowid
        conn.commit()

        cur.close(); conn.close()
        return redirect(url_for('ticket_view', ticket_id=ticket_id))

    cur.close(); conn.close()
    return render_template("book_ticket.html", lines=lines)

# -------- TICKET VIEW --------
def qr(data):
    img=qrcode.make(data)
    buf=io.BytesIO()
    img.save(buf,format="PNG")
    return "data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode()

@app.route('/ticket/<int:ticket_id>')
@login_required
def ticket_view(ticket_id):
    conn=get_conn(); cur=conn.cursor(dictionary=True)
    cur.execute("""
        SELECT t.*, m.line_name, s1.stop_name AS from_name, s2.stop_name AS to_name 
        FROM tickets t
        JOIN metro_lines m ON t.line_id=m.line_id
        JOIN stops s1 ON t.from_stop=s1.stop_id
        JOIN stops s2 ON t.to_stop=s2.stop_id
        WHERE t.ticket_id=%s
    """,(ticket_id,))
    t=cur.fetchone()
    cur.close(); conn.close()
    if not t:
        flash("Ticket not found", "danger")
        return redirect(url_for('dashboard'))
    return render_template("ticket_view.html",ticket=t,qr_img=qr(f"ticket_id={ticket_id}"))

# -------- GET TRAINS API --------
@app.route('/get_trains')
@login_required
def get_trains():
    try:
        line_id = int(request.args.get('line_id'))
        from_stop = int(request.args.get('from_stop'))
        to_stop = int(request.args.get('to_stop'))
    except:
        return jsonify([])

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT stop_order FROM stops WHERE stop_id=%s", (from_stop,))
    s1 = cur.fetchone()
    cur.execute("SELECT stop_order FROM stops WHERE stop_id=%s", (to_stop,))
    s2 = cur.fetchone()

    direction = 'UP' if s1['stop_order'] < s2['stop_order'] else 'DOWN'

    cur.execute("""
        SELECT schedule_id, arrival_time, departure_time, direction
        FROM train_schedule
        WHERE line_id=%s AND stop_id=%s AND direction=%s
        ORDER BY departure_time LIMIT 10
    """, (line_id, from_stop, direction))

    rows = cur.fetchall()
    cur.close(); conn.close()

    result = []
    for r in rows:
        result.append({
            "schedule_id": r["schedule_id"],
            "arrival_time": format_time(r["arrival_time"]),
            "departure_time": format_time(r["departure_time"]),
            "direction": r["direction"]
        })

    return jsonify(result)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))


@app.route('/admin/register', methods=['GET', 'POST'])
@login_required
def admin_register():
    # Only admins allowed
    if current_user.role_name != "admin":
        flash("Admin access required", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        # Check if email already exists
        cur.execute("SELECT user_id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            cur.close(); conn.close()
            flash("Email already registered!", "danger")
            return redirect(url_for('admin_register'))

        pwd_hash = generate_password_hash(password)

        cur2 = conn.cursor()
        # role_id = 1 → ADMIN
        cur2.execute("""
            INSERT INTO users(name, email, role_id, password_hash)
            VALUES (%s, %s, 1, %s)
        """, (name, email, pwd_hash))

        conn.commit()
        cur.close(); cur2.close(); conn.close()

        flash("Admin account created successfully!", "success")
        return redirect(url_for('admin_register'))

    return render_template("admin_register.html")

# ADMIN ACCESS CONTROL
# --------------------------------------------------------
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Login required", "danger")
            return redirect(url_for("login"))
        if current_user.role_name != "admin":
            flash("You are not allowed to access admin pages", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


# --------------------------------------------------------
# ADMIN: DASHBOARD
# --------------------------------------------------------
@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    return render_template("admin/admin_dashboard.html")


# --------------------------------------------------------
# ADMIN: MANAGE USERS
# --------------------------------------------------------
@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id, name, email, role_id FROM users")
    users = cur.fetchall()
    cur.close(); conn.close()

    return render_template("admin/admin_users.html", users=users)


# --------------------------------------------------------
# ADMIN: MANAGE LINES
# --------------------------------------------------------
@app.route("/admin/lines", methods=["GET", "POST"])
@login_required
@admin_required
def admin_lines():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        line_name = request.form["line_name"]
        cur.execute("INSERT INTO metro_lines(line_name) VALUES(%s)", (line_name,))
        conn.commit()

    cur.execute("SELECT * FROM metro_lines")
    lines = cur.fetchall()
    cur.close(); conn.close()

    return render_template("admin/admin_lines.html", lines=lines)


# --------------------------------------------------------
# ADMIN: MANAGE STOPS
# --------------------------------------------------------
@app.route("/admin/stops", methods=["GET", "POST"])
@login_required
@admin_required
def admin_stops():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        stop_name = request.form["stop_name"]
        line_id = request.form["line_id"]
        stop_order = request.form["stop_order"]
        cur.execute("INSERT INTO stops(stop_name, line_id, stop_order) VALUES(%s, %s, %s)",
                    (stop_name, line_id, stop_order))
        conn.commit()

    cur.execute("""
        SELECT s.*, m.line_name 
        FROM stops s JOIN metro_lines m ON s.line_id = m.line_id
        ORDER BY s.line_id, s.stop_order
    """)
    stops = cur.fetchall()

    cur.execute("SELECT * FROM metro_lines")
    lines = cur.fetchall()

    cur.close(); conn.close()

    return render_template("admin/admin_stops.html", stops=stops, lines=lines)


# --------------------------------------------------------
# ADMIN: TRAIN SCHEDULE
# --------------------------------------------------------
@app.route("/admin/schedule", methods=["GET", "POST"])
@login_required
@admin_required
def admin_schedule():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        line_id = request.form["line_id"]
        stop_id = request.form["stop_id"]
        direction = request.form["direction"]
        arrival_time = request.form["arrival_time"]
        departure_time = request.form["departure_time"]

        cur.execute("""
            INSERT INTO train_schedule(line_id, stop_id, direction, arrival_time, departure_time)
            VALUES(%s, %s, %s, %s, %s)
        """, (line_id, stop_id, direction, arrival_time, departure_time))

        conn.commit()

    cur.execute("""
        SELECT ts.*, m.line_name, s.stop_name
        FROM train_schedule ts
        JOIN metro_lines m ON ts.line_id = m.line_id
        JOIN stops s ON ts.stop_id = s.stop_id
        ORDER BY ts.line_id, ts.stop_id
    """)
    schedule = cur.fetchall()

    cur.execute("SELECT * FROM metro_lines")
    lines = cur.fetchall()

    cur.execute("SELECT stop_id, stop_name, line_id FROM stops")
    stops = cur.fetchall()

    cur.close(); conn.close()

    return render_template("admin/admin_schedule.html", schedule=schedule, stops=stops, lines=lines)

if __name__=="__main__":
    app.run(debug=True)
    
# --------------------------------------------------------

