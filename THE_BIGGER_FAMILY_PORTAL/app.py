import os
import json
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db, calculate_age, is_eligible_age

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'the-bigger-family-portal-secret-key-2026')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db():
    if 'db' not in g:
        g.db = get_db_connection()
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ----------------- Context Processors & Decorators -----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'member_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'member_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') not in ['admin', 'branch_leader']:
            flash('Admin or Branch Leader privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def load_logged_in_member():
    member_id = session.get('member_id')
    if member_id is None:
        g.member = None
        g.unread_notif_count = 0
    else:
        conn = get_db()
        member = conn.execute('''
            SELECT m.*, b.name as branch_name, b.color_code as branch_color
            FROM members m
            JOIN branches b ON m.branch_id = b.id
            WHERE m.id = ?
        ''', (member_id,)).fetchone()
        g.member = member

        # Count unread notifications (direct + broadcast not yet read)
        if member:
            unread_count = conn.execute('''
                SELECT COUNT(*) as count FROM notifications n
                WHERE (n.member_id = ? AND n.is_read = 0)
                   OR (n.member_id IS NULL AND n.id NOT IN (
                       SELECT notification_id FROM broadcast_reads WHERE member_id = ?
                   ))
            ''', (member_id, member_id)).fetchone()['count']
            g.unread_notif_count = unread_count
        else:
            g.unread_notif_count = 0

@app.context_processor
def inject_global_settings():
    conn = get_db()
    settings = conn.execute('SELECT * FROM dues_settings WHERE is_active = 1 LIMIT 1').fetchone()
    return {
        'dues_settings': settings,
        'family_name': 'The Bigger Family',
        'current_year': date.today().year,
        'today_date': date.today().strftime('%Y-%m-%d')
    }

# ----------------- Helper Functions -----------------

def create_notification(title, message, category='announcement', priority='normal', action_link=None, member_id=None):
    """Creates a notification. If member_id is None, it is a broadcast to all."""
    conn = get_db()
    conn.execute('''
        INSERT INTO notifications (member_id, title, message, category, priority, action_link)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (member_id, title, message, category, priority, action_link))
    conn.commit()
    # conn.close() handled by teardown

# ----------------- Public & Auth Routes -----------------

@app.route('/')
def index():
    if 'member_id' in session:
        return redirect(url_for('dashboard'))
    conn = get_db()
    branches = conn.execute('SELECT * FROM branches ORDER BY id ASC').fetchall()
    member_count = conn.execute('SELECT COUNT(*) as count FROM members').fetchone()['count']
    branch_count = conn.execute('SELECT COUNT(*) as count FROM branches').fetchone()['count']
    next_meeting = conn.execute('''
        SELECT * FROM meetings 
        WHERE status = 'upcoming' AND scheduled_date >= DATE('now')
        ORDER BY scheduled_date ASC, start_time ASC LIMIT 1
    ''').fetchone()
    # conn.close() handled by teardown
    return render_template('index.html', branches=branches, member_count=member_count, branch_count=branch_count, next_meeting=next_meeting)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'member_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db()
        member = conn.execute('SELECT * FROM members WHERE email = ?', (email,)).fetchone()
    # conn.close() handled by teardown

        if member and check_password_hash(member['password_hash'], password):
            if member['status'] != 'active':
                flash('Your account is awaiting family administration approval.', 'warning')
                return render_template('login.html', email=email)
            
            session.clear()
            session['member_id'] = member['id']
            session['full_name'] = member['full_name']
            session['role'] = member['role']
            session['branch_id'] = member['branch_id']
            flash(f'Welcome back, {member["full_name"]}!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'member_id' in session:
        return redirect(url_for('dashboard'))

    conn = get_db()
    branches = conn.execute('SELECT id, name FROM branches ORDER BY name ASC').fetchall()
    elders = conn.execute('SELECT id, full_name, role FROM members ORDER BY full_name ASC').fetchall()
    # conn.close() handled by teardown

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        date_of_birth = request.form.get('date_of_birth', '').strip()
        gender = request.form.get('gender', '').strip()
        branch_id = request.form.get('branch_id', '').strip()
        occupation = request.form.get('occupation', '').strip()
        residence = request.form.get('residence', '').strip()
        bio = request.form.get('bio', '').strip()
        parent_id = request.form.get('parent_member_id')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 1. Strict 16+ Age Verification
        if not date_of_birth:
            flash('Please enter your valid date of birth.', 'danger')
            return render_template('register.html', branches=branches, elders=elders, form=request.form)

        age = calculate_age(date_of_birth)
        if age < 16:
            flash(f'Eligibility Restriction: Member registration is strictly reserved for family members aged 16 years and above. According to your date of birth, you are currently {age} years old. Younger dependents can be registered through their parent.', 'danger')
            return render_template('register.html', branches=branches, elders=elders, form=request.form)

        # 2. Validation
        if not full_name or not email or not phone or not branch_id or not password:
            flash('Please fill in all mandatory fields.', 'danger')
            return render_template('register.html', branches=branches, elders=elders, form=request.form)

        if password != confirm_password:
            flash('Passwords do not match. Please verify.', 'danger')
            return render_template('register.html', branches=branches, elders=elders, form=request.form)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html', branches=branches, elders=elders, form=request.form)

        conn = get_db()
        # Check existing email
        existing = conn.execute('SELECT id FROM members WHERE email = ?', (email,)).fetchone()
        if existing:
    # conn.close() handled by teardown
            flash('An account with this email address already exists. Please log in.', 'warning')
            return render_template('register.html', branches=branches, elders=elders, form=request.form)

        password_hash = generate_password_hash(password)
        parent_val = int(parent_id) if parent_id and parent_id.isdigit() else None

        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO members (branch_id, full_name, email, phone, date_of_birth, age, gender, occupation, residence, bio, parent_member_id, role, status, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'member', 'active', ?)
        ''', (int(branch_id), full_name, email, phone, date_of_birth, age, gender, occupation, residence, bio, parent_val, password_hash))
        new_member_id = cursor.lastrowid

        # Auto-create current month's dues bill for new 16+ member
        today = date.today()
        curr_period = today.strftime('%Y-%m')
        curr_label = today.strftime('%B %Y')
        settings = conn.execute('SELECT monthly_amount FROM dues_settings WHERE is_active = 1 LIMIT 1').fetchone()
        amount_due = settings['monthly_amount'] if settings else 50.00

        cursor.execute('''
            INSERT OR IGNORE INTO dues_records (member_id, period_month, period_label, amount_due, amount_paid, status)
            VALUES (?, ?, ?, ?, 0.00, 'unpaid')
        ''', (new_member_id, curr_period, curr_label, amount_due))

        # Create Welcome Notification
        cursor.execute('''
            INSERT INTO notifications (member_id, title, message, category, priority, action_link)
            VALUES (?, ?, ?, 'member', 'normal', ?)
        ''', (new_member_id, 'Welcome to The Bigger Family Portal!', f'Akwaaba {full_name}! Your membership has been registered under your family branch. You are now eligible to participate in bi-weekly meetings and family welfare decisions.', '/profile'))

        # Broadcast announcement to family
        cursor.execute('''
            INSERT INTO notifications (member_id, title, message, category, priority, action_link)
            VALUES (NULL, ?, ?, 'member', 'normal', ?)
        ''', ('New Family Member Registered (16+ Cohort)', f'{full_name} (Age {age}) has officially registered on the portal under their family branch. Let us extend a warm family welcome!', '/family-tree'))

        conn.commit()
    # conn.close() handled by teardown

        # Log in newly registered member
        session.clear()
        session['member_id'] = new_member_id
        session['full_name'] = full_name
        session['role'] = 'member'
        session['branch_id'] = int(branch_id)

        flash(f'Welcome to The Bigger Family, {full_name}! Your age ({age} years) was successfully verified.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html', branches=branches, elders=elders)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been securely logged out.', 'info')
    return redirect(url_for('index'))

# ----------------- Dashboard Route -----------------

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    member_id = session['member_id']
    today_str = date.today().strftime('%Y-%m-%d')
    curr_period = date.today().strftime('%Y-%m')

    # My Current Month Dues Record
    my_current_dues = conn.execute('''
        SELECT * FROM dues_records 
        WHERE member_id = ? AND period_month = ?
    ''', (member_id, curr_period)).fetchone()

    # My Total Outstanding Dues Balance
    dues_summary = conn.execute('''
        SELECT 
            SUM(amount_due) as total_billed,
            SUM(amount_paid) as total_paid
        FROM dues_records
        WHERE member_id = ?
    ''', (member_id,)).fetchone()
    
    total_billed = dues_summary['total_billed'] or 0.0
    total_paid = dues_summary['total_paid'] or 0.0
    outstanding_balance = max(0.0, total_billed - total_paid)

    # Next Bi-Weekly Meeting
    next_meeting = conn.execute('''
        SELECT m.*, a.rsvp_status,
        (SELECT COUNT(*) FROM attendance WHERE meeting_id = m.id AND rsvp_status = 'attending') as attending_count
        FROM meetings m
        LEFT JOIN attendance a ON m.id = a.meeting_id AND a.member_id = ?
        WHERE m.status = 'upcoming' AND m.scheduled_date >= ?
        ORDER BY m.scheduled_date ASC, m.start_time ASC LIMIT 1
    ''', (member_id, today_str)).fetchone()

    # Recent In-App Alerts (top 4 for user)
    alerts = conn.execute('''
        SELECT n.*, 
            CASE 
                WHEN n.member_id IS NULL THEN (
                    SELECT 1 FROM broadcast_reads WHERE notification_id = n.id AND member_id = ?
                )
                ELSE n.is_read
            END as user_has_read
        FROM notifications n
        WHERE n.member_id = ? OR n.member_id IS NULL
        ORDER BY n.created_at DESC LIMIT 5
    ''', (member_id, member_id)).fetchall()

    # Family Tree Quick Stats
    branch_stats = conn.execute('''
        SELECT b.id, b.name, b.color_code, COUNT(m.id) as count
        FROM branches b
        LEFT JOIN members m ON b.id = m.branch_id
        GROUP BY b.id
        ORDER BY count DESC
    ''').fetchall()

    total_family_members = conn.execute('SELECT COUNT(*) as c FROM members').fetchone()['c']

    # conn.close() handled by teardown

    return render_template('dashboard.html',
                           my_current_dues=my_current_dues,
                           outstanding_balance=outstanding_balance,
                           total_paid=total_paid,
                           next_meeting=next_meeting,
                           alerts=alerts,
                           branch_stats=branch_stats,
                           total_family_members=total_family_members)

# ----------------- Family Tree & Branches -----------------

@app.route('/family-tree')
@login_required
def family_tree():
    conn = get_db()
    branches = conn.execute('''
        SELECT b.*, COUNT(m.id) as member_count
        FROM branches b
        LEFT JOIN members m ON b.id = m.branch_id
        GROUP BY b.id
        ORDER BY b.id ASC
    ''').fetchall()

    members = conn.execute('''
        SELECT m.id, m.full_name, m.age, m.gender, m.role, m.occupation, m.residence, m.parent_member_id,
               b.name as branch_name, b.color_code as branch_color, p.full_name as parent_name
        FROM members m
        JOIN branches b ON m.branch_id = b.id
        LEFT JOIN members p ON m.parent_member_id = p.id
        ORDER BY m.branch_id ASC, m.age DESC
    ''').fetchall()
    # conn.close() handled by teardown

    return render_template('family_tree.html', branches=branches, members=members)

@app.route('/branch/<int:branch_id>')
@login_required
def branch_detail(branch_id):
    conn = get_db()
    branch = conn.execute('SELECT * FROM branches WHERE id = ?', (branch_id,)).fetchone()
    if not branch:
    # conn.close() handled by teardown
        flash('Branch not found.', 'danger')
        return redirect(url_for('family_tree'))

    members = conn.execute('''
        SELECT m.*, p.full_name as parent_name
        FROM members m
        LEFT JOIN members p ON m.parent_member_id = p.id
        WHERE m.branch_id = ?
        ORDER BY m.age DESC
    ''', (branch_id,)).fetchall()

    # Dues compliance for this branch
    curr_period = date.today().strftime('%Y-%m')
    dues_stats = conn.execute('''
        SELECT 
            COUNT(d.id) as total_dues_records,
            SUM(CASE WHEN d.status = 'paid' THEN 1 ELSE 0 END) as paid_count,
            SUM(d.amount_paid) as total_collected
        FROM dues_records d
        JOIN members m ON d.member_id = m.id
        WHERE m.branch_id = ? AND d.period_month = ?
    ''', (branch_id, curr_period)).fetchone()

    # conn.close() handled by teardown
    return render_template('branch_detail.html', branch=branch, members=members, dues_stats=dues_stats, curr_period=curr_period)

# ----------------- Monthly Dues & Welfare Fund -----------------

@app.route('/dues')
@login_required
def dues():
    conn = get_db()
    member_id = session['member_id']
    is_admin = session.get('role') in ['admin', 'branch_leader']

    # My personal dues history
    my_records = conn.execute('''
        SELECT d.*, m.full_name as verified_by_name
        FROM dues_records d
        LEFT JOIN members m ON d.verified_by = m.id
        WHERE d.member_id = ?
        ORDER BY d.period_month DESC
    ''', (member_id,)).fetchall()

    # Dues settings
    settings = conn.execute('SELECT * FROM dues_settings WHERE is_active = 1 LIMIT 1').fetchone()

    # Totals for current member
    summary = conn.execute('''
        SELECT 
            SUM(amount_due) as total_due,
            SUM(amount_paid) as total_paid
        FROM dues_records
        WHERE member_id = ?
    ''', (member_id,)).fetchone()
    
    total_due = summary['total_due'] or 0.0
    total_paid = summary['total_paid'] or 0.0
    balance_owed = max(0.0, total_due - total_paid)

    # If Admin, load pending approvals & overall family collection
    pending_records = []
    family_stats = None
    if is_admin:
        pending_records = conn.execute('''
            SELECT d.*, m.full_name, m.phone, b.name as branch_name
            FROM dues_records d
            JOIN members m ON d.member_id = m.id
            JOIN branches b ON m.branch_id = b.id
            WHERE d.status = 'pending_verification'
            ORDER BY d.payment_date DESC
        ''').fetchall()

        family_stats = conn.execute('''
            SELECT 
                SUM(amount_due) as total_billed,
                SUM(amount_paid) as total_collected,
                COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_count,
                COUNT(*) as total_records
            FROM dues_records
        ''').fetchone()

    # conn.close() handled by teardown
    return render_template('dues.html',
                           my_records=my_records,
                           settings=settings,
                           total_due=total_due,
                           total_paid=total_paid,
                           balance_owed=balance_owed,
                           pending_records=pending_records,
                           family_stats=family_stats,
                           is_admin=is_admin)

@app.route('/dues/pay', methods=['POST'])
@login_required
def pay_dues():
    member_id = session['member_id']
    record_id = request.form.get('record_id')
    period_month = request.form.get('period_month')
    payment_method = request.form.get('payment_method', 'MTN MoMo')
    transaction_ref = request.form.get('transaction_reference', '').strip()
    notes = request.form.get('notes', '').strip()
    amount_paid = float(request.form.get('amount_paid', 50.00))

    if not transaction_ref:
        flash('Please provide the transaction reference / SMS confirmation ID.', 'danger')
        return redirect(url_for('dues'))

    conn = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if record_id and str(record_id).isdigit():
        conn.execute('''
            UPDATE dues_records
            SET amount_paid = ?, payment_method = ?, transaction_reference = ?,
                payment_date = ?, status = 'pending_verification', admin_notes = ?
            WHERE id = ? AND member_id = ?
        ''', (amount_paid, payment_method, transaction_ref, now_str, notes, int(record_id), member_id))
    else:
        # Create or update on conflict
        label = datetime.strptime(period_month, '%Y-%m').strftime('%B %Y')
        settings = conn.execute('SELECT monthly_amount FROM dues_settings WHERE is_active = 1 LIMIT 1').fetchone()
        amount_due = settings['monthly_amount'] if settings else 50.00
        conn.execute('''
            INSERT INTO dues_records 
            (member_id, period_month, period_label, amount_due, amount_paid, status, payment_method, transaction_reference, payment_date, admin_notes)
            VALUES (?, ?, ?, ?, ?, 'pending_verification', ?, ?, ?, ?)
            ON CONFLICT(member_id, period_month) DO UPDATE SET
                amount_paid = excluded.amount_paid,
                payment_method = excluded.payment_method,
                transaction_reference = excluded.transaction_reference,
                payment_date = excluded.payment_date,
                status = 'pending_verification',
                admin_notes = excluded.admin_notes
        ''', (member_id, period_month, label, amount_due, amount_paid, payment_method, transaction_ref, now_str, notes))

    conn.commit()
    # conn.close() handled by teardown

    flash('Payment submission received! The family treasurer will verify your reference code shortly.', 'success')
    return redirect(url_for('dues'))

@app.route('/dues/approve/<int:record_id>', methods=['POST'])
@admin_required
def approve_dues(record_id):
    admin_id = session['member_id']
    conn = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    record = conn.execute('SELECT d.*, m.full_name, m.id as m_id FROM dues_records d JOIN members m ON d.member_id = m.id WHERE d.id = ?', (record_id,)).fetchone()
    if not record:
    # conn.close() handled by teardown
        flash('Record not found.', 'danger')
        return redirect(url_for('dues'))

    conn.execute('''
        UPDATE dues_records
        SET status = 'paid', verified_by = ?, verified_at = ?, admin_notes = 'Approved by Family Welfare Administrator'
        WHERE id = ?
    ''', (admin_id, now_str, record_id))

    # Create notification for member
    conn.execute('''
        INSERT INTO notifications (member_id, title, message, category, priority, action_link)
        VALUES (?, ?, ?, 'dues', 'normal', ?)
    ''', (record['m_id'], f'Dues Payment Approved ({record["period_label"]})', f'Your monthly dues payment of GH₵ {record["amount_paid"]:.2f} for {record["period_label"]} has been verified. Your digital receipt is ready.', f'/dues/receipt/{record_id}'))

    conn.commit()
    # conn.close() handled by teardown

    flash(f'Dues payment for {record["full_name"]} verified and receipt issued!', 'success')
    return redirect(url_for('dues'))

@app.route('/dues/receipt/<int:record_id>')
@login_required
def dues_receipt(record_id):
    conn = get_db()
    member_id = session['member_id']
    is_admin = session.get('role') in ['admin', 'branch_leader']

    record = conn.execute('''
        SELECT d.*, m.full_name, m.email, m.phone, b.name as branch_name, v.full_name as verifier_name
        FROM dues_records d
        JOIN members m ON d.member_id = m.id
        JOIN branches b ON m.branch_id = b.id
        LEFT JOIN members v ON d.verified_by = v.id
        WHERE d.id = ?
    ''', (record_id,)).fetchone()

    # conn.close() handled by teardown

    if not record:
        flash('Receipt not found.', 'danger')
        return redirect(url_for('dues'))

    if record['member_id'] != member_id and not is_admin:
        flash('Unauthorized to view this receipt.', 'danger')
        return redirect(url_for('dues'))

    return render_template('receipt.html', record=record)

# ----------------- Bi-Weekly Meetings (Every 2 Weeks) -----------------

@app.route('/meetings')
@login_required
def meetings():
    conn = get_db()
    member_id = session['member_id']
    today_str = date.today().strftime('%Y-%m-%d')
    is_admin = session.get('role') in ['admin', 'branch_leader']

    # Upcoming meetings (scheduled every 2 weeks)
    upcoming = conn.execute('''
        SELECT m.*, a.rsvp_status,
        (SELECT COUNT(*) FROM attendance WHERE meeting_id = m.id AND rsvp_status = 'attending') as attending_count,
        (SELECT COUNT(*) FROM attendance WHERE meeting_id = m.id AND rsvp_status = 'tentative') as tentative_count,
        (SELECT COUNT(*) FROM attendance WHERE meeting_id = m.id AND rsvp_status = 'absent') as absent_count
        FROM meetings m
        LEFT JOIN attendance a ON m.id = a.meeting_id AND a.member_id = ?
        WHERE m.status = 'upcoming' AND m.scheduled_date >= ?
        ORDER BY m.scheduled_date ASC
    ''', (member_id, today_str)).fetchall()

    # Past completed meetings
    past = conn.execute('''
        SELECT m.*, a.attended, a.rsvp_status,
        (SELECT COUNT(*) FROM attendance WHERE meeting_id = m.id AND attended = 1) as total_attended
        FROM meetings m
        LEFT JOIN attendance a ON m.id = a.meeting_id AND a.member_id = ?
        WHERE m.status = 'completed' OR m.scheduled_date < ?
        ORDER BY m.scheduled_date DESC
    ''', (member_id, today_str)).fetchall()

    # conn.close() handled by teardown
    return render_template('meetings.html', upcoming=upcoming, past=past, is_admin=is_admin)

@app.route('/meetings/<int:meeting_id>')
@login_required
def meeting_detail(meeting_id):
    conn = get_db()
    member_id = session['member_id']
    is_admin = session.get('role') in ['admin', 'branch_leader']

    meeting = conn.execute('SELECT * FROM meetings WHERE id = ?', (meeting_id,)).fetchone()
    if not meeting:
    # conn.close() handled by teardown
        flash('Meeting not found.', 'danger')
        return redirect(url_for('meetings'))

    my_attendance = conn.execute('SELECT * FROM attendance WHERE meeting_id = ? AND member_id = ?', (meeting_id, member_id)).fetchone()
    
    # Attendees list
    attendees = conn.execute('''
        SELECT a.*, m.full_name, m.phone, b.name as branch_name, b.color_code as branch_color
        FROM attendance a
        JOIN members m ON a.member_id = m.id
        JOIN branches b ON m.branch_id = b.id
        WHERE a.meeting_id = ?
        ORDER BY a.rsvp_status ASC, m.full_name ASC
    ''', (meeting_id,)).fetchall()

    all_members = []
    if is_admin:
        all_members = conn.execute('SELECT id, full_name FROM members ORDER BY full_name ASC').fetchall()

    # conn.close() handled by teardown
    return render_template('meeting_detail.html', meeting=meeting, my_attendance=my_attendance, attendees=attendees, all_members=all_members, is_admin=is_admin)

@app.route('/meetings/rsvp/<int:meeting_id>', methods=['POST'])
@login_required
def meeting_rsvp(meeting_id):
    member_id = session['member_id']
    rsvp_status = request.form.get('rsvp_status', 'attending')
    notes = request.form.get('rsvp_notes', '')

    conn = get_db()
    conn.execute('''
        INSERT INTO attendance (meeting_id, member_id, rsvp_status, rsvp_notes, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(meeting_id, member_id) DO UPDATE SET
            rsvp_status = excluded.rsvp_status,
            rsvp_notes = excluded.rsvp_notes,
            updated_at = CURRENT_TIMESTAMP
    ''', (meeting_id, member_id, rsvp_status, notes))
    conn.commit()
    # conn.close() handled by teardown

    status_labels = {'attending': 'Attending', 'tentative': 'Tentative', 'absent': 'Apology Sent'}
    flash(f'Your RSVP ({status_labels.get(rsvp_status, rsvp_status)}) has been recorded.', 'success')
    return redirect(request.referrer or url_for('meetings'))

@app.route('/meetings/new', methods=['POST'])
@admin_required
def create_meeting():
    title = request.form.get('title', '').strip()
    meeting_type = request.form.get('meeting_type', 'Bi-Weekly General Assembly')
    scheduled_date = request.form.get('scheduled_date')
    start_time = request.form.get('start_time', '16:00')
    end_time = request.form.get('end_time', '18:00')
    location_type = request.form.get('location_type', 'virtual')
    location_detail = request.form.get('location_detail', '').strip()
    agenda = request.form.get('agenda', '').strip()

    if not title or not scheduled_date or not location_detail:
        flash('Please fill in title, date, and location/link.', 'danger')
        return redirect(url_for('meetings'))

    conn = get_db()
    # Find next cycle number
    last_cycle = conn.execute('SELECT MAX(cycle_number) as max_c FROM meetings').fetchone()['max_c'] or 25
    next_cycle = last_cycle + 1

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO meetings (title, meeting_type, scheduled_date, start_time, end_time, location_type, location_detail, agenda, cycle_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'upcoming')
    ''', (title, meeting_type, scheduled_date, start_time, end_time, location_type, location_detail, agenda, next_cycle))
    meeting_id = cursor.lastrowid

    # Broadcast notification to all family members
    cursor.execute('''
        INSERT INTO notifications (member_id, title, message, category, priority, action_link)
        VALUES (NULL, ?, ?, 'meeting', 'urgent', ?)
    ''', (f'New Bi-Weekly Meeting: {title}', f'The next bi-weekly assembly has been scheduled for {scheduled_date} at {start_time}. Please review the agenda and RSVP.', f'/meetings/{meeting_id}'))

    conn.commit()
    # conn.close() handled by teardown

    flash(f'Meeting scheduled and notification sent to all family members!', 'success')
    return redirect(url_for('meetings'))

@app.route('/meetings/save-minutes/<int:meeting_id>', methods=['POST'])
@admin_required
def save_meeting_minutes(meeting_id):
    minutes = request.form.get('minutes', '').strip()
    status = request.form.get('status', 'completed')

    conn = get_db()
    conn.execute('''
        UPDATE meetings 
        SET minutes = ?, status = ?
        WHERE id = ?
    ''', (minutes, status, meeting_id))
    conn.commit()
    # conn.close() handled by teardown

    flash('Meeting minutes and resolutions published successfully.', 'success')
    return redirect(url_for('meeting_detail', meeting_id=meeting_id))

# ----------------- In-App Notifications Hub -----------------

@app.route('/notifications')
@login_required
def notifications():
    member_id = session['member_id']
    conn = get_db()

    category_filter = request.args.get('category')
    
    query = '''
        SELECT n.*,
            CASE 
                WHEN n.member_id IS NULL THEN (
                    SELECT 1 FROM broadcast_reads WHERE notification_id = n.id AND member_id = ?
                )
                ELSE n.is_read
            END as is_already_read
        FROM notifications n
        WHERE (n.member_id = ? OR n.member_id IS NULL)
    '''
    params = [member_id, member_id]

    if category_filter in ['meeting', 'dues', 'member', 'announcement']:
        query += ' AND n.category = ?'
        params.append(category_filter)

    query += ' ORDER BY n.created_at DESC'

    notifs = conn.execute(query, params).fetchall()
    # conn.close() handled by teardown

    return render_template('notifications.html', notifications=notifs, active_category=category_filter)

@app.route('/notifications/read/<int:notif_id>')
@login_required
def mark_notification_read(notif_id):
    member_id = session['member_id']
    conn = get_db()

    notif = conn.execute('SELECT * FROM notifications WHERE id = ?', (notif_id,)).fetchone()
    if notif:
        if notif['member_id'] is None:
            # Broadcast notification
            conn.execute('''
                INSERT OR IGNORE INTO broadcast_reads (notification_id, member_id)
                VALUES (?, ?)
            ''', (notif_id, member_id))
        elif notif['member_id'] == member_id:
            conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ?', (notif_id,))
        conn.commit()

    # conn.close() handled by teardown
    if notif and notif['action_link']:
        return redirect(notif['action_link'])
    return redirect(url_for('notifications'))

@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    member_id = session['member_id']
    conn = get_db()

    # Mark direct notifications as read
    conn.execute('UPDATE notifications SET is_read = 1 WHERE member_id = ?', (member_id,))

    # Mark all existing broadcasts as read for this member
    broadcasts = conn.execute('SELECT id FROM notifications WHERE member_id IS NULL').fetchall()
    for b in broadcasts:
        conn.execute('''
            INSERT OR IGNORE INTO broadcast_reads (notification_id, member_id)
            VALUES (?, ?)
        ''', (b['id'], member_id))

    conn.commit()
    # conn.close() handled by teardown
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))

@app.route('/notifications/broadcast', methods=['POST'])
@admin_required
def broadcast_notification():
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    category = request.form.get('category', 'announcement')
    priority = request.form.get('priority', 'normal')
    action_link = request.form.get('action_link', '').strip() or None

    if not title or not message:
        flash('Please fill in both title and message.', 'danger')
        return redirect(url_for('notifications'))

    create_notification(title, message, category, priority, action_link, member_id=None)
    flash('Broadcast alert successfully sent to all family members!', 'success')
    return redirect(url_for('notifications'))

# ----------------- Member Profile -----------------

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    member_id = session['member_id']
    conn = get_db()

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        occupation = request.form.get('occupation', '').strip()
        residence = request.form.get('residence', '').strip()
        bio = request.form.get('bio', '').strip()

        conn.execute('''
            UPDATE members 
            SET phone = ?, occupation = ?, residence = ?, bio = ?
            WHERE id = ?
        ''', (phone, occupation, residence, bio, member_id))
        conn.commit()
        flash('Your profile has been updated.', 'success')

    member = conn.execute('''
        SELECT m.*, b.name as branch_name, b.color_code as branch_color, p.full_name as parent_name
        FROM members m
        JOIN branches b ON m.branch_id = b.id
        LEFT JOIN members p ON m.parent_member_id = p.id
        WHERE m.id = ?
    ''', (member_id,)).fetchone()
    # conn.close() handled by teardown

    return render_template('profile.html', member=member)

# ----------------- Admin Console -----------------

@app.route('/admin')
@admin_required
def admin_panel():
    conn = get_db()

    members = conn.execute('''
        SELECT m.*, b.name as branch_name
        FROM members m
        JOIN branches b ON m.branch_id = b.id
        ORDER BY m.id DESC
    ''').fetchall()

    branches = conn.execute('''
        SELECT b.*, COUNT(m.id) as member_count
        FROM branches b
        LEFT JOIN members m ON b.id = m.branch_id
        GROUP BY b.id
    ''').fetchall()

    settings = conn.execute('SELECT * FROM dues_settings WHERE is_active = 1 LIMIT 1').fetchone()
    # conn.close() handled by teardown

    return render_template('admin.html', members=members, branches=branches, settings=settings)

@app.route('/admin/branches/create', methods=['POST'])
@admin_required
def create_branch():
    name = request.form.get('name', '').strip()
    leader_name = request.form.get('leader_name', '').strip()
    description = request.form.get('description', '').strip()
    color_code = request.form.get('color_code', '#3B82F6').strip()
    slug = name.lower().replace(' ', '-').replace("'", '')

    if not name:
        flash('Branch name is required.', 'danger')
        return redirect(url_for('admin_panel'))

    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO branches (name, slug, leader_name, description, color_code)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, slug, leader_name, description, color_code))
        conn.commit()
        flash(f'New branch "{name}" created successfully.', 'success')
    except Exception as e:
        flash(f'Error creating branch: {e}', 'danger')

    return redirect(url_for('admin_panel'))

@app.route('/admin/dues/generate-month', methods=['POST'])
@admin_required
def generate_monthly_dues():
    """Generates monthly dues records for all active 16+ members for the specified month."""
    period_month = request.form.get('period_month') # YYYY-MM
    if not period_month:
        today = date.today()
        period_month = today.strftime('%Y-%m')

    period_label = datetime.strptime(period_month, '%Y-%m').strftime('%B %Y')

    conn = get_db()
    settings = conn.execute('SELECT monthly_amount FROM dues_settings WHERE is_active = 1 LIMIT 1').fetchone()
    amount = settings['monthly_amount'] if settings else 50.00

    active_members = conn.execute("SELECT id FROM members WHERE status = 'active'").fetchall()
    created_count = 0

    for m in active_members:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO dues_records (member_id, period_month, period_label, amount_due, amount_paid, status)
            VALUES (?, ?, ?, ?, 0.00, 'unpaid')
        ''', (m['id'], period_month, period_label, amount))
        if cursor.rowcount > 0:
            created_count += 1

    # Send broadcast notification
    if created_count > 0:
        create_notification(
            title=f'Monthly Welfare Dues Generated ({period_label})',
            message=f'Welfare dues of GH₵ {amount:.2f} for {period_label} have been posted for all family members. Please submit your payment via MoMo to 024 456 7890.',
            category='dues',
            priority='urgent',
            action_link='/dues'
        )

    conn.commit()
    # conn.close() handled by teardown

    flash(f'Generated {created_count} monthly dues records for {period_label}. In-app alert dispatched.', 'success')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5000)
