import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date

# ---------------- DATABASE ----------------
conn = sqlite3.connect("hostel.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    subscription TEXT DEFAULT 'trial'
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    name TEXT,
    contact TEXT,
    room_type TEXT,
    rent INTEGER,
    building TEXT,
    status TEXT,
    created_at TEXT,
    join_date TEXT,
    checkout_date TEXT,
    security_deposit INTEGER,
    monthly_rent INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    owner_id INTEGER,
    amount INTEGER,
    paid_for_month TEXT,
    paid_on TEXT
)
""")
conn.commit()


c.execute("CREATE TABLE IF NOT EXISTS room_config (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, room_type TEXT, building TEXT, capacity INTEGER, rent INTEGER)")
conn.commit()



# ---------------- HELPERS ----------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

ROOM_RENT = {
    "Single": 6000,
    "2 Sharing": 4500,
    "2 Sharing (Attached Bathroom)": 5500,
    "3 Sharing": 3500
}
def setup_rooms(owner_id):
    st.write("Configure Rooms & Rent")
    room_types = ["Single","2 Sharing","2 Sharing (Attached Bathroom)","3 Sharing"]
    for r in room_types:
        c.execute("SELECT capacity,rent FROM room_config WHERE owner_id=? AND room_type=?", (owner_id,r))
        row = c.fetchone()
        cap = row[0] if row else 0
        rent = row[1] if row else 0
        new_cap = st.number_input(r+" Capacity", min_value=0, value=cap, key="cap_"+r)
        new_rent = st.number_input(r+" Rent", min_value=0, value=rent, key="rent_"+r)
        if st.button("Save "+r, key="save_"+r):
            c.execute("DELETE FROM room_config WHERE owner_id=? AND room_type=?", (owner_id,r))
            c.execute("INSERT INTO room_config (owner_id,room_type,capacity,rent) VALUES (?,?,?,?)", (owner_id,r,new_cap,new_rent))
            conn.commit()
            st.success(r+" saved")

def vacancy_data(owner_id):
    c.execute(
        "SELECT room_type, capacity FROM room_config WHERE owner_id=?",
        (owner_id,)
    )
    configs = c.fetchall()

    result = []
    for room_type, capacity in configs:
        c.execute(
            "SELECT COUNT(*) FROM tenants WHERE owner_id=? AND room_type=? AND status='active'",
            (owner_id, room_type)
        )
        occupied = c.fetchone()[0]
        vacant = capacity - occupied
        result.append((room_type, occupied, vacant))

    return result


def tenant_balance(tenant_id):
    c.execute("SELECT join_date, monthly_rent FROM tenants WHERE id=?", (tenant_id,))
    row = c.fetchone()
    if not row:
        return 0, 0, 0

    join_date, rent = row
    jd = datetime.strptime(join_date, "%Y-%m-%d").date()
    today = date.today()

    months = (today.year - jd.year) * 12 + (today.month - jd.month) + 1
    expected = months * rent

    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE tenant_id=?", (tenant_id,))
    paid = c.fetchone()[0]

    remaining = expected - paid
    return expected, paid, remaining

def checkout_summary(tenant_id):
    c.execute(
        "SELECT security_deposit FROM tenants WHERE id=?",
        (tenant_id,)
    )
    deposit = c.fetchone()[0] or 0

    expected, paid, remaining = tenant_balance(tenant_id)

    refund = deposit - remaining
    return expected, paid, remaining, deposit, refund
    
def load_demo_data(owner_id):
    tenants = [
        ("Aman", "999000001", "Single", 5000, 3000),
        ("Rohit", "999000002", "2 Sharing", 4000, 3000),
        ("Suresh", "999000003", "2 Sharing", 4000, 3000),
        ("Vikas", "999000004", "3 Sharing", 3000, 2000),
        ("Ankit", "999000005", "Single", 5000, 3000),
        ("Rahul", "999000006", "3 Sharing", 3000, 2000),
        ("Deepak", "999000007", "2 Sharing", 4000, 3000),
        ("Nitin", "999000008", "Single", 5000, 3000),
        ("Manoj", "999000009", "3 Sharing", 3000, 2000),
        ("Kunal", "999000010", "2 Sharing", 4000, 3000),
    ]

    for t in tenants:
        c.execute("""
        INSERT INTO tenants
        (owner_id, name, contact, room_type, monthly_rent, security_deposit, join_date, status)
        VALUES (?, ?, ?, ?, ?, ?, DATE('now','-2 months'), 'active')
        """, (owner_id, t[0], t[1], t[2], t[3], t[4]))

    conn.commit()
        
# ---------------- SESSION ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ---------------- AUTH ----------------
def login():
    st.subheader("Login")

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_btn"):
        c.execute("SELECT id, password FROM users WHERE email=?", (email,))
        u = c.fetchone()

        if u and u[1] == hash_password(password):
            st.session_state.user_id = u[0]
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid login")


def signup():
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    if st.button("Signup", key="signup_btn"):
        try:
            c.execute("INSERT INTO users (email,password) VALUES (?,?)", (email, hash_password(password)))
            conn.commit()
            st.success("Account created")
        except:
            st.error("Email already exists")


# ---------------- TENANT FUNCTIONS ----------------
def record_payment(owner_id):
    st.subheader("Record Tenant Payment")

    tenants = c.execute(
        "SELECT id, name FROM tenants WHERE owner_id=? AND status='active'",
        (owner_id,)
    ).fetchall()

    if not tenants:
        st.info("No active tenants")
        return

    tenant_map = {f"{t[1]} (ID:{t[0]})": t[0] for t in tenants}
    selected = st.selectbox("Select Tenant", list(tenant_map.keys()))

    amount = st.number_input("Amount Paid", min_value=0)
    month = st.selectbox(
        "Paid For Month",
        ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    )

    if st.button("Save Payment"):
        c.execute(
            "INSERT INTO payments (tenant_id, owner_id, amount, paid_for_month, paid_on) VALUES (?,?,?,?,DATE('now'))",
            (tenant_map[selected], owner_id, amount, month)
        )
        conn.commit()
        st.success("Payment recorded")
             

def add_tenant(owner_id):
    name = st.text_input("Tenant Name")
    contact = st.text_input("Contact Number")
    room_type = st.selectbox("Room Type", ["Single","2 Sharing","2 Sharing (Attached Bathroom)","3 Sharing"])
    c.execute("SELECT rent FROM room_config WHERE owner_id=? AND room_type=?", (owner_id,room_type))
    r = c.fetchone()
    rent = r[0] if r else 0
    building = st.text_input("Building No (Optional)")
    st.write("Monthly Rent: ₹", rent)
    if st.button("Add Tenant"):
        if rent == 0:
            st.error("Please configure rooms first")
        else:
            c.execute("INSERT INTO tenants (owner_id,name,contact,room_type,rent,building,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                      (owner_id,name,contact,room_type,rent,building,"active",datetime.now().isoformat()))
            conn.commit()
            st.success("Tenant added")


def list_tenants(owner_id, status):
    c.execute("""
    SELECT id, name, contact, room_type, rent, building 
    FROM tenants WHERE owner_id=? AND status=?
    """, (owner_id, status))
    return c.fetchall()

def checkout_tenant(tenant_id):
    c.execute("UPDATE tenants SET status='checked_out' WHERE id=?", (tenant_id,))
    conn.commit()

# ---------------- DASHBOARD ----------------
def dashboard():
    st.title("Hostel Management System")
    st.divider()
    st.subheader("Active Tenant Balances")
    tenants = c.execute("SELECT id, name, join_date, monthly_rent FROM tenants WHERE owner_id=? AND status='active'",
    (st.session_state.user_id,)).fetchall()
    if not tenants:
        st.info("No active tenants")
    else:
        for t in tenants:
            expected, paid, remaining = tenant_balance(t[0])
            st.write(
                f"""
                **{t[1]}**
                | Joined: {t[2]}
                | Rent: ₹{t[3]}
                | Paid: ₹{paid}
                | Due: ₹{remaining}
                """
            )
    st.subheader("Vacancy Status")
    data = vacancy_data(st.session_state.user_id)
    if not data:
        st.info("No room configuration found")
    else:
        for d in data:
            st.write(
                f"{d[0]} | Occupied: {d[1]} | Vacant: {d[2]}"
            )
    
    if st.button("Load Demo Data (Temporary)"):
        load_demo_data(st.session_state.user_id)
        st.success("Demo data loaded")
        st.rerun()

    st.sidebar.title("Hostel Menu")

    menu = st.sidebar.radio("Menu", ["Dashboard","Room Setup","Record Payment","Add Tenant","Active Tenants","Vacancy Dashboard","Checked-out Tenants","Logout"])
                            
    if menu == "Dashboard":
        st.subheader("Welcome to Dashboard")
        st.write("Select an option from sidebar")
    elif menu == "Room Setup":
        setup_rooms(st.session_state.user_id)
    elif menu == "Record Payment":
        record_payment(st.session_state.user_id)
    elif menu == "Add Tenant":
        add_tenant(st.session_state.user_id)
    elif menu == "Vacancy Dashboard":
        data = vacancy_data(st.session_state.user_id)
        if not data:
            st.info("Please configure rooms first")
        for d in data:
            st.write(d[0], "| Occupied:", d[1], "| Vacant:", d[2])

    elif menu == "Active Tenants":
        st.subheader("Active Tenants")
        tenants = c.execute(
            "SELECT id, name FROM tenants WHERE owner_id=? AND status='active'",
            (st.session_state.user_id,)
        ).fetchall()
        for t in tenants:
            with st.expander(t[1]):
                expected, paid, remaining, deposit, refund = checkout_summary(t[0])
                st.write(f"Total Rent Till Date: ₹{expected}")
                st.write(f"Total Paid: ₹{paid}")
                st.write(f"Outstanding Due: ₹{remaining}")
                st.write(f"Security Deposit: ₹{deposit}")
                if refund >= 0:
                    st.success(f"Refund to Tenant: ₹{refund}")
                else:
                    st.error(f"Amount to Collect: ₹{-refund}")
                if st.button("Checkout Tenant", key=f"checkout_{t[0]}"):
                    c.execute("UPDATE tenants SET status='checked_out', checkout_date=DATE('now') WHERE id=?",
                              (t[0],)
                             )
                    conn.commit()
                    st.success("Tenant checked out successfully")
                    st.rerun()

    elif menu == "Checked-out Tenants":
        st.subheader("Checked-out Tenants")
        tenants = list_tenants(st.session_state.user_id, "checked_out")
        for t in tenants:
            st.write(f"{t[1]} | {t[3]} | ₹{t[4]}")

    elif menu == "Logout":
        st.session_state.user_id = None
        st.rerun()

# ---------------- MAIN ----------------

if st.session_state.user_id is None:
    tab1, tab2 = st.tabs(["Login", "Signup"])
    with tab1:
        login()
    with tab2:
        signup()
else:
    dashboard()
