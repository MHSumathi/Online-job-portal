import unittest
from app import app
from database import init_db

class TestOnlineJobPortal(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        init_db(seed=True)

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Discover The Right Job', response.data)
        self.assertIn(b'JobPortal', response.data)

    def test_jobs_page(self):
        response = self.client.get('/jobs')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Browse Job Vacancies', response.data)

    def test_jobs_filter(self):
        response = self.client.get('/jobs?q=Python&type=Full-Time')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Senior Python', response.data)

    def test_job_detail_page(self):
        response = self.client.get('/jobs/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TechCorp Solutions', response.data)
        self.assertIn(b'Job Snapshot', response.data)

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign In to Your Account', response.data)
        self.assertIn(b'Quick 1-Click Demo Logins', response.data)

    def test_seeker_demo_login_and_dashboard(self):
        response = self.client.get('/demo-login/seeker', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alex Rivera', response.data)
        self.assertIn(b'My Job Applications', response.data)

    def test_employer_demo_login_and_dashboard(self):
        response = self.client.get('/demo-login/employer', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TechCorp Solutions', response.data)
        self.assertIn(b'Managed Job Postings', response.data)

    def test_admin_demo_login_and_dashboard(self):
        response = self.client.get('/demo-login/admin', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Platform Administration', response.data)
        self.assertIn(b'User Directory', response.data)

if __name__ == '__main__':
    unittest.main()
