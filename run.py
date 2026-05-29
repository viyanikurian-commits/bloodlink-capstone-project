from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()

app.secret_key = os.getenv("SECRET_KEY")

bcrypt = Bcrypt(app)

app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST")
app.config['MYSQL_USER'] = os.getenv("MYSQL_USER")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB")

mysql = MySQL(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        college_id = request.form['college_id']
        location = request.form['location']
        blood_group = request.form['blood_group']
        password = request.form['password']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO users
            (full_name, email, phone, college_id, location, blood_group, password, availability_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            full_name, email, phone, college_id, location,
            blood_group, hashed_password, "Available"
        ))

        mysql.connection.commit()
        cursor.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.check_password_hash(user[7], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['blood_group'] = user[6]
            return redirect("/dashboard")

        return """
        <script>
            alert('Invalid Email or Password');
            window.location.href='/login';
        </script>
        """

    return render_template("login.html")


@app.route("/admin-login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admins WHERE email=%s", (email,))
        admin = cursor.fetchone()
        cursor.close()

        if admin and admin[3] == password:
            session['admin_id'] = admin[0]
            session['admin_name'] = admin[1]
            return redirect("/admin-dashboard")

        return """
        <script>
            alert('Invalid Admin Email or Password');
            window.location.href='/admin-login';
        </script>
        """

    return render_template("admin_login.html")


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT full_name, blood_group, availability_status
        FROM users
        WHERE id=%s
    """, (session['user_id'],))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT message, location, phone, created_at
        FROM broadcasts
        WHERE blood_group=%s
        ORDER BY created_at DESC
    """, (user[1],))

    broadcasts = cursor.fetchall()
    cursor.close()

    return render_template(
        "dashboard.html",
        name=user[0],
        blood_group=user[1],
        availability=user[2],
        broadcasts=broadcasts
    )


@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    return render_template("profile.html", user=user)


@app.route("/edit-profile", methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    if request.method == 'POST':
        full_name = request.form['full_name']
        phone = request.form['phone']
        college_id = request.form['college_id']
        location = request.form['location']
        blood_group = request.form['blood_group']

        cursor.execute("""
            UPDATE users
            SET full_name=%s, phone=%s, college_id=%s, location=%s, blood_group=%s
            WHERE id=%s
        """, (
            full_name, phone, college_id, location,
            blood_group, session['user_id']
        ))

        mysql.connection.commit()
        cursor.close()

        session['user_name'] = full_name
        session['blood_group'] = blood_group

        return redirect("/profile")

    cursor.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    return render_template("edit_profile.html", user=user)


@app.route("/availability", methods=['GET', 'POST'])
def availability():
    if 'user_id' not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    if request.method == 'POST':
        status = request.form['availability_status']

        cursor.execute("""
            UPDATE users
            SET availability_status=%s
            WHERE id=%s
        """, (status, session['user_id']))

        mysql.connection.commit()

    cursor.execute("""
        SELECT availability_status
        FROM users
        WHERE id=%s
    """, (session['user_id'],))

    status = cursor.fetchone()
    cursor.close()

    return render_template("availability.html", status=status[0])


@app.route("/search", methods=['GET', 'POST'])
def search():
    if 'user_id' not in session:
        return redirect("/login")

    donors = []

    if request.method == 'POST':
        blood_group = request.form['blood_group']

        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, full_name, blood_group, location, availability_status
            FROM users
            WHERE blood_group=%s
            AND id!=%s
        """, (
            blood_group,
            session['user_id']
        ))

        donors = cursor.fetchall()
        cursor.close()

    return render_template("search.html", donors=donors)


@app.route("/send-request/<int:donor_id>")
def send_request(donor_id):
    if 'user_id' not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT blood_group, location
        FROM users
        WHERE id=%s
    """, (donor_id,))

    donor = cursor.fetchone()

    cursor.execute("""
        INSERT INTO requests
        (requester_id, donor_id, blood_group, location, message, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        session['user_id'],
        donor_id,
        donor[0],
        donor[1],
        "Emergency blood request",
        "Pending"
    ))

    mysql.connection.commit()
    cursor.close()

    return """
    <script>
        alert('Blood request sent successfully!');
        window.location.href='/tracking';
    </script>
    """


@app.route("/tracking")
def tracking():
    if 'user_id' not in session:
        return redirect("/login")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
            r.id,
            u.full_name,
            r.blood_group,
            r.location,
            r.status,
            r.created_at
        FROM requests r
        JOIN users u ON r.donor_id = u.id
        WHERE r.requester_id=%s
        ORDER BY r.created_at DESC
    """, (session['user_id'],))

    requests_data = cursor.fetchall()
    cursor.close()

    return render_template("tracking.html", requests_data=requests_data)


@app.route("/history")
def history():
    return render_template("history.html")


@app.route("/admin-dashboard")
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect("/admin-login")

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT id, blood_group, location, phone, message, created_at
        FROM broadcasts
        ORDER BY created_at DESC
    """)

    broadcasts = cursor.fetchall()
    cursor.close()

    return render_template("admin_dashboard.html", broadcasts=broadcasts)


@app.route("/broadcast", methods=['GET', 'POST'])
def broadcast():
    if 'admin_id' not in session:
        return redirect("/admin-login")

    if request.method == 'POST':
        blood_group = request.form['blood_group']
        location = request.form['location']
        phone = request.form['phone']
        message = request.form['message']

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO broadcasts
            (blood_group, location, phone, message)
            VALUES (%s, %s, %s, %s)
        """, (blood_group, location, phone, message))

        mysql.connection.commit()
        cursor.close()

        return """
        <script>
            alert('Broadcast sent successfully!');
            window.location.href='/admin-dashboard';
        </script>
        """

    return render_template("broadcast.html")


@app.route("/delete-broadcast/<int:broadcast_id>")
def delete_broadcast(broadcast_id):
    if 'admin_id' not in session:
        return redirect("/admin-login")

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM broadcasts WHERE id=%s", (broadcast_id,))
    mysql.connection.commit()
    cursor.close()

    return """
    <script>
        alert('Broadcast deleted successfully!');
        window.location.href='/admin-dashboard';
    </script>
    """


@app.route("/request-popup")
def request_popup():
    return render_template("request_popup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)