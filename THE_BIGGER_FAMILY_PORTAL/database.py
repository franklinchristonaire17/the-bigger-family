import sqlite3
import os
import shutil
from datetime import datetime, date

ORIGINAL_DB_PATH = os.path.join(os.path.dirname(__file__), 'family_portal.db')
if os.environ.get('VERCEL'):
    TMP_DB_PATH = '/tmp/family_portal.db'
    if not os.path.exists(TMP_DB_PATH) and os.path.exists(ORIGINAL_DB_PATH):
        try:
            shutil.copy2(ORIGINAL_DB_PATH, TMP_DB_PATH)
        except Exception:
            pass
    DB_PATH = TMP_DB_PATH
else:
    DB_PATH = ORIGINAL_DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Branches table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        leader_name TEXT,
        description TEXT,
        color_code TEXT DEFAULT '#3B82F6',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Members table (16+ rule)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id INTEGER NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        date_of_birth DATE NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        occupation TEXT,
        residence TEXT,
        bio TEXT,
        parent_member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
        role TEXT DEFAULT 'member', -- 'admin', 'branch_leader', 'elder', 'member'
        status TEXT DEFAULT 'active', -- 'active', 'pending_approval'
        profile_photo TEXT,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Dues Settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dues_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        monthly_amount REAL NOT NULL DEFAULT 50.00,
        currency TEXT DEFAULT 'GH₵',
        due_day_of_month INTEGER DEFAULT 28,
        momo_number TEXT DEFAULT '024 456 7890',
        momo_name TEXT DEFAULT 'The Bigger Family Welfare Fund',
        bank_name TEXT DEFAULT 'GCB Bank / Ecobank Ghana',
        bank_account TEXT DEFAULT '1441002345678',
        is_active INTEGER DEFAULT 1,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Dues Records table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dues_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
        period_month TEXT NOT NULL, -- Format: YYYY-MM e.g. '2026-11'
        period_label TEXT NOT NULL, -- e.g. 'November 2026'
        amount_due REAL NOT NULL,
        amount_paid REAL DEFAULT 0.00,
        status TEXT DEFAULT 'unpaid', -- 'unpaid', 'pending_verification', 'paid', 'exempt'
        payment_method TEXT, -- 'MTN MoMo', 'Telecel Cash', 'AT Money', 'Bank Transfer', 'Cash'
        transaction_reference TEXT,
        proof_filename TEXT,
        payment_date DATETIME,
        verified_by INTEGER REFERENCES members(id),
        verified_at DATETIME,
        admin_notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(member_id, period_month)
    )
    ''')

    # Bi-weekly Meetings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        meeting_type TEXT DEFAULT 'Bi-Weekly General Assembly',
        scheduled_date DATE NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        location_type TEXT NOT NULL DEFAULT 'virtual', -- 'virtual', 'physical', 'hybrid'
        location_detail TEXT NOT NULL,
        agenda TEXT,
        minutes TEXT,
        status TEXT DEFAULT 'upcoming', -- 'upcoming', 'in_progress', 'completed', 'cancelled'
        cycle_number INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Attendance & RSVP table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
        member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
        rsvp_status TEXT DEFAULT 'pending', -- 'attending', 'tentative', 'absent'
        rsvp_notes TEXT,
        attended INTEGER DEFAULT 0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(meeting_id, member_id)
    )
    ''')

    # Notifications Hub table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER REFERENCES members(id) ON DELETE CASCADE, -- NULL for all members
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        category TEXT DEFAULT 'announcement', -- 'meeting', 'dues', 'member', 'announcement'
        priority TEXT DEFAULT 'normal', -- 'normal', 'urgent'
        action_link TEXT,
        is_read INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Notification read tracking for broadcast notifications
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS broadcast_reads (
        notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
        member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
        read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (notification_id, member_id)
    )
    ''')

    conn.commit()
    conn.close()

def calculate_age(birth_date_str):
    """Calculates age in years from YYYY-MM-DD string."""
    try:
        if isinstance(birth_date_str, str):
            dob = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        else:
            dob = birth_date_str
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except Exception:
        return 0

def is_eligible_age(birth_date_str):
    """Checks if member is strictly 16 years old or above."""
    return calculate_age(birth_date_str) >= 16

if __name__ == '__main__':
    init_db()
    print("Database schema successfully initialized.")
