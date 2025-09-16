from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.errors
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load Together.ai key
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Gmail credentials from .env
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

app = Flask(__name__)
CORS(app)

DB_NAME = os.getenv("DB_NAME", "hr_onboarding")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "2121")
DB_HOST = os.getenv("DB_HOST", "localhost")

# ---------- Bootstrap Database + Table ----------
def init_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        database="postgres",
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Create database if not exists
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}';")
    if not cur.fetchone():
        cur.execute(f"CREATE DATABASE {DB_NAME};")
        print(f"✅ Database {DB_NAME} created.")
    else:
        print(f"ℹ️ Database {DB_NAME} already exists.")

    cur.close()
    conn.close()

    # Now connect to HR database
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Create employees table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        role VARCHAR(100) NOT NULL,
        email VARCHAR(150) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("✅ Table employees is ready.")

    cur.close()
    conn.close()


# ---------- Helper for connections ----------
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

# ---------- AI Email Generation with Together.ai ----------
def generate_welcome_email(name, role, field, organization):
    if not TOGETHER_API_KEY:
        return f"Welcome {name}! We are excited for you to join {organization} as our new {role}. (AI email skipped — no Together.ai key set)"

    try:
        headers = {"Authorization": f"Bearer {TOGETHER_API_KEY}"}
        
        # New, more detailed prompt
        prompt = (f"Write a warm and professional HR welcome email for a new employee named {name}. "
                  f"They are joining the company '{organization}' as a '{role}'. "
                  f"The company operates in the {field} sector. "
                  f"The email should be welcoming, mention their role and the company name, and have a positive tone suitable for the {field} industry.")

        data = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "prompt": prompt,
            "max_tokens": 100, # Increased token limit for a more detailed email
            "temperature": 0.7
        }

        res = requests.post("https://api.together.xyz/v1/completions", headers=headers, json=data)
        result = res.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["text"].strip()
        else:
            # Fallback message with the new details
            return f"Welcome {name}! We're excited to have you at {organization} as our new {role}."

    except Exception as e:
        return f"(AI email generation failed: {e})"

# ---------- Email Sender ----------
def send_email(to, subject, body):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("⚠️ Email credentials not set. Skipping email.")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to, msg.as_string())
        print(f"📧 Email sent to {to}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


# ---------- API Endpoints ----------
@app.route("/employees", methods=["POST"])
def add_employee():
    data = request.json
    name = data["name"]
    role = data["role"]
    email = data["email"]
    field = data["field"]
    organization = data["organization"]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO employees (name, role, email) VALUES (%s, %s, %s) RETURNING id;",
            (name, role, email)
        )
        emp_id = cur.fetchone()[0]
        conn.commit()

        # Onboarding checklist
        checklist = [
            f"Create email account for {name}",
            f"Set up workstation for {name}",
            "Assign buddy/mentor",
            f"Schedule HR introduction session for the {field} team"
        ]

        # AI-powered welcome email with new context
        welcome_email = generate_welcome_email(name, role, field, organization)

        # Send the email
        send_email(email, f"Welcome to {organization}!", welcome_email)

        return jsonify({
            "message": f"Employee {name} added successfully!",
            "employee_id": emp_id,
            "checklist": checklist,
            "welcome_email": welcome_email
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        conn.close()


@app.route("/employees", methods=["GET"])
def get_employees():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM employees ORDER BY id;")
    employees = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(employees)


# ---------- Update Employee ----------
@app.route("/employees/<int:emp_id>", methods=["PUT"])
def update_employee(emp_id):
    data = request.json
    name, role, email = data["name"], data["role"], data["email"]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "UPDATE employees SET name=%s, role=%s, email=%s WHERE id=%s RETURNING id;",
            (name, role, email, emp_id)
        )
        updated = cur.fetchone()
        conn.commit()

        if updated:
            return jsonify({"message": f"Employee {emp_id} updated successfully!"})
        else:
            return jsonify({"error": f"Employee {emp_id} not found"}), 404

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        conn.close()


# ---------- Delete Employee ----------
@app.route("/employees/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM employees WHERE id=%s RETURNING id;", (emp_id,))
        deleted = cur.fetchone()
        conn.commit()

        if deleted:
            return jsonify({"message": f"Employee {emp_id} deleted successfully!"})
        else:
            return jsonify({"error": f"Employee {emp_id} not found"}), 404

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)