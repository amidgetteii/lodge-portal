import streamlit as st
import sqlite3
import hashlib
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Eureka Lodge No. 3 Portal",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
        .main { background-color: #0f172a; color: #f8fafc; }
        .stSidebar { background-color: #1e293b; }
        h1, h2, h3 { color: #fbbf24 !important; }
        .card { background-color: #1e293b; padding: 20px; border-radius: 10px; border-left: 5px solid #fbbf24; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "eureka_lodge.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Create tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT DEFAULT 'Member')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, date TEXT NOT NULL, content TEXT NOT NULL, author TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, filename TEXT NOT NULL, uploader TEXT NOT NULL)''')
    
    # Safely upgrade old database (adds role column if it's missing)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Member'")
    except sqlite3.OperationalError:
        pass 
        
    # Default announcements
    cursor.execute("SELECT COUNT(*) FROM announcements")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO announcements (title, date, content, author) VALUES (?, ?, ?, ?)",
                       ("Spring Fish Fry Fundraiser", "May 2026", "Join us for our annual Spring Fish Fry Fundraiser at 820 Cumberland St. Plates include fish, sides, and a drink. Support the lodge's community initiatives! Flyer designed by Bro. Alvin F. Midgette, II.", "Fundraising Committee"))
    conn.commit()
    conn.close()

init_db()

def make_hash(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hash(password, hashed_text): return make_hash(password) == hashed_text

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "username" not in st.session_state: st.session_state.username = ""
if "role" not in st.session_state: st.session_state.role = "Member"

# --- AUTHENTICATION SCREEN ---
def show_auth_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""<div style='text-align: center; margin-bottom: -10px;'>
            <img src='https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Square_compasses.svg/200px-Square_compasses.svg.png' width='120'/></div>""", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; margin-top: 0;'>Eureka Lodge No. 3</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8;'>F&AM PHA • Fayetteville, NC</p>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
        with tab1:
            with st.form("signin_form"):
                email = st.text_input("Email Address").strip().lower()
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    if email and password:
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("SELECT password, role FROM users WHERE email = ?", (email,))
                        result = cursor.fetchone()
                        conn.close()
                        if result and check_hash(password, result[0]):
                            st.session_state.authenticated = True
                            st.session_state.username = email
                            st.session_state.role = result[1]
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
        with tab2:
            with st.form("signup_form"):
                new_email = st.text_input("Email Address").strip().lower()
                new_pass = st.text_input("Password", type="password")
                confirm_pass = st.text_input("Confirm Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if new_email and new_pass == confirm_pass:
                        try:
                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()
                            # Make the first user an Admin automatically
                            cursor.execute("SELECT COUNT(*) FROM users")
                            is_first_user = cursor.fetchone()[0] == 0
                            role = "Admin" if is_first_user else "Member"
                            
                            cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (new_email, make_hash(new_pass), role))
                            conn.commit()
                            conn.close()
                            
                            st.session_state.authenticated = True
                            st.session_state.username = new_email
                            st.session_state.role = role
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Account already exists.")
                    else:
                        st.error("Passwords must match.")

# --- MAIN DASHBOARD ---
def show_dashboard():
    st.sidebar.markdown("""<div style='text-align: center;'>
        <img src='https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Square_compasses.svg/200px-Square_compasses.svg.png' width='80'/>
        <h3 style='margin-top: 10px;'>Eureka Lodge No. 3</h3></div>""", unsafe_allow_html=True)
    st.sidebar.markdown(f"**Logged in as:** `{st.session_state.username}`")
    st.sidebar.markdown(f"**Role:** `{st.session_state.role}`")
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navigation", ["📢 Announcements", "👥 Member Directory", "👤 Membership Status", "🖼️ Media Gallery"])
    st.sidebar.markdown("---")
    if st.sidebar.button("Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    # --- ANNOUNCEMENTS ---
    if menu == "📢 Announcements":
        st.title("Lodge Announcements")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT title, date, content, author FROM announcements ORDER BY id DESC")
        for title, date, content, author in cursor.fetchall():
            st.markdown(f"<div class='card'><h3>{title}</h3><p><strong>Date:</strong> {date} | <strong>Author:</strong> {author}</p><p>{content}</p></div>", unsafe_allow_html=True)
        conn.close()
        
        # ONLY show the publisher tool to Admins
        if st.session_state.role == "Admin":
            with st.expander("➕ Post New Announcement (Admin Only)"):
                with st.form("announcement_form"):
                    new_title = st.text_input("Title")
                    new_date = st.text_input("Date / Period")
                    new_content = st.text_area("Details")
                    if st.form_submit_button("Publish") and new_title:
                        conn = sqlite3.connect(DB_FILE)
                        conn.cursor().execute("INSERT INTO announcements (title, date, content, author) VALUES (?, ?, ?, ?)", (new_title, new_date, new_content, st.session_state.username))
                        conn.commit()
                        conn.close()
                        st.rerun()

    # --- MEMBER DIRECTORY ---
    elif menu == "👥 Member Directory":
        st.title("Member Directory")
        st.markdown("A roster of all brothers registered on the portal.")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT email, role FROM users ORDER BY role ASC, email ASC")
        members = cursor.fetchall()
        conn.close()
        
        for email, role in members:
            role_color = "#fbbf24" if role == "Admin" else "#94a3b8"
            st.markdown(f"""
            <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 1.1em; font-weight: bold;">{email}</span>
                <span style="background-color: #0f172a; padding: 5px 15px; border-radius: 20px; color: {role_color}; font-weight: bold;">{role}</span>
            </div>
            """, unsafe_allow_html=True)

    # --- MEMBERSHIP STATUS ---
    elif menu == "👤 Membership Status":
        st.title("Membership Profile")
        st.markdown(f"""
        <div class="card">
            <h3>Member Details</h3>
            <p><strong>Lodge:</strong> Eureka Lodge No. 3</p>
            <p><strong>Account Email:</strong> {st.session_state.username}</p>
            <p><strong>Portal Role:</strong> {st.session_state.role}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- MEDIA GALLERY ---
    elif menu == "🖼️ Media Gallery":
        st.title("Lodge Media Gallery")
        os.makedirs("uploads", exist_ok=True)
        with st.form("media_upload_form", clear_on_submit=True):
            media_title = st.text_input("Media Title / Description")
            uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])
            if st.form_submit_button("Upload File") and uploaded_file:
                with open(os.path.join("uploads", uploaded_file.name), "wb") as f: f.write(uploaded_file.getbuffer())
                conn = sqlite3.connect(DB_FILE)
                conn.cursor().execute("INSERT INTO media (title, filename, uploader) VALUES (?, ?, ?)", (media_title, uploaded_file.name, st.session_state.username))
                conn.commit()
                conn.close()
                st.rerun()
        
        st.markdown("---")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT title, filename, uploader FROM media ORDER BY id DESC")
        items = cursor.fetchall()
        conn.close()
        cols = st.columns(2)
        for idx, (title, filename, uploader) in enumerate(items):
            if os.path.exists(os.path.join("uploads", filename)):
                with cols[idx % 2]: st.image(os.path.join("uploads", filename), caption=f"{title} (By: {uploader})", use_container_width=True)

if not st.session_state.authenticated: show_auth_screen()
else: show_dashboard()