import unittest
from datetime import date, timedelta
from app import app
from database import init_db, get_db_connection
import seed_data

class FamilyPortalTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        seed_data.seed()

    def setUp(self):
        self.client = app.test_client()
        self.client.get('/logout')

    def test_landing_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'THE BIGGER FAMILY', response.data)
        self.assertIn(b'One Lineage, Many Branches', response.data)

    def test_age_restriction_under_16(self):
        """Verify that someone under 16 CANNOT register."""
        conn = get_db_connection()
        branch = conn.execute("SELECT id FROM branches LIMIT 1").fetchone()
        branch_id = str(branch['id'])
        conn.close()

        # 14 years old
        dob_under_16 = (date.today() - timedelta(days=14*365)).strftime('%Y-%m-%d')
        response = self.client.post('/register', data={
            'full_name': 'Younger Child Bigger',
            'email': 'child@biggerfamily.org',
            'phone': '+233 24 000 1111',
            'date_of_birth': dob_under_16,
            'gender': 'Male',
            'branch_id': branch_id,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        self.assertIn(b'Eligibility Restriction', response.data)
        conn = get_db_connection()
        member = conn.execute("SELECT * FROM members WHERE email = 'child@biggerfamily.org'").fetchone()
        conn.close()
        self.assertIsNone(member)

    def test_registration_eligible_16_plus(self):
        """Verify that someone aged 16+ CAN register successfully."""
        conn = get_db_connection()
        branch = conn.execute("SELECT id FROM branches LIMIT 1").fetchone()
        branch_id = str(branch['id'])
        conn.close()

        # Exactly 17 years old
        dob_17 = (date.today() - timedelta(days=17*365)).strftime('%Y-%m-%d')
        response = self.client.post('/register', data={
            'full_name': 'Kofi Eligible Bigger',
            'email': 'kofi.eligible@biggerfamily.org',
            'phone': '+233 24 999 8888',
            'date_of_birth': dob_17,
            'gender': 'Male',
            'branch_id': branch_id,
            'occupation': 'Student',
            'residence': 'Accra',
            'bio': 'Eager to join the family portal.',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Akwaaba, Kofi Eligible Bigger!', response.data)

        # Check DB and dues record
        conn = get_db_connection()
        member = conn.execute("SELECT * FROM members WHERE email = 'kofi.eligible@biggerfamily.org'").fetchone()
        self.assertIsNotNone(member)
        self.assertGreaterEqual(member['age'], 16)

        # Current dues record should be created
        dues = conn.execute("SELECT * FROM dues_records WHERE member_id = ?", (member['id'],)).fetchone()
        self.assertIsNotNone(dues)
        self.assertEqual(dues['amount_due'], 50.00)
        conn.close()

    def test_login_and_dashboard(self):
        # Login as Admin
        response = self.client.post('/login', data={
            'email': 'admin@biggerfamily.org',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Elder Kofi Kwabena Bigger', response.data)
        self.assertIn(b'Bi-Weekly Meeting', response.data)

    def test_dues_payment_and_admin_approval(self):
        # 1. Login as Serwaa
        self.client.post('/login', data={
            'email': 'serwaa.bigger@outlook.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Submit payment
        curr_period = date.today().strftime('%Y-%m')
        pay_res = self.client.post('/dues/pay', data={
            'period_month': curr_period,
            'payment_method': 'MTN MoMo',
            'transaction_reference': 'MOMO-TEST-12345',
            'amount_paid': '50.00',
            'notes': 'Test payment reference'
        }, follow_redirects=True)
        self.assertIn(b'Payment submission received!', pay_res.data)

        # Logout Serwaa first
        self.client.get('/logout')

        # 2. Login as Admin & approve
        self.client.post('/login', data={
            'email': 'admin@biggerfamily.org',
            'password': 'admin123'
        }, follow_redirects=True)

        conn = get_db_connection()
        rec = conn.execute("SELECT id FROM dues_records WHERE transaction_reference = 'MOMO-TEST-12345'").fetchone()
        self.assertIsNotNone(rec)
        rec_id = rec['id']
        conn.close()

        approve_res = self.client.post(f'/dues/approve/{rec_id}', follow_redirects=True)
        self.assertIn(b'verified and receipt issued', approve_res.data)

        # Receipt view
        receipt_res = self.client.get(f'/dues/receipt/{rec_id}')
        self.assertEqual(receipt_res.status_code, 200)
        self.assertIn(b'Official Receipt', receipt_res.data)

    def test_biweekly_meetings_and_rsvp(self):
        # Login as Dr. Kwesi
        self.client.post('/login', data={
            'email': 'kwesi.bigger@gmail.com',
            'password': 'password123'
        }, follow_redirects=True)

        meetings_res = self.client.get('/meetings')
        self.assertEqual(meetings_res.status_code, 200)
        self.assertIn(b'Bi-Weekly Family Assemblies', meetings_res.data)

        # RSVP Attending
        conn = get_db_connection()
        meeting = conn.execute("SELECT id FROM meetings WHERE status = 'upcoming' LIMIT 1").fetchone()
        conn.close()

        rsvp_res = self.client.post(f'/meetings/rsvp/{meeting["id"]}', data={
            'rsvp_status': 'attending',
            'rsvp_notes': 'Will be attending via Zoom.'
        }, follow_redirects=True)
        self.assertIn(b'Your RSVP (Attending) has been recorded', rsvp_res.data)

    def test_in_app_notifications(self):
        self.client.post('/login', data={
            'email': 'admin@biggerfamily.org',
            'password': 'admin123'
        }, follow_redirects=True)

        notif_res = self.client.get('/notifications')
        self.assertEqual(notif_res.status_code, 200)
        self.assertIn(b'In-App Notifications', notif_res.data)

        # Mark all read
        read_res = self.client.post('/notifications/read-all', follow_redirects=True)
        self.assertIn(b'All notifications marked as read', read_res.data)

if __name__ == '__main__':
    unittest.main()
