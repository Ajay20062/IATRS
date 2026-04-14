import json
import time
from urllib import request, error

from db_connect import get_db_connection

BASE = 'http://127.0.0.1:5001'


def call(method, path, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    req = request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode('utf-8')
            return resp.status, json.loads(text) if text else {}
    except error.HTTPError as exc:
        text = exc.read().decode('utf-8')
        return exc.code, json.loads(text) if text else {}


def main():
    suffix = str(int(time.time()))
    candidate_email = f'candidate.{suffix}@mail.com'
    recruiter_email = f'recruiter.{suffix}@mail.com'
    password = 'StrongPass123'

    status, candidate_reg = call('POST', '/register/candidate', {
        'full_name': 'Candidate Test',
        'email': candidate_email,
        'phone': '9999999999',
        'password': password,
    })
    assert status == 201, f'Candidate registration failed: {status} {candidate_reg}'
    candidate_id = candidate_reg['candidate_id']

    status, recruiter_reg = call('POST', '/register/recruiter', {
        'full_name': 'Recruiter Test',
        'email': recruiter_email,
        'company': 'ATS Labs',
        'password': password
    })
    assert status == 201, f'Recruiter registration failed: {status} {recruiter_reg}'
    recruiter_id = recruiter_reg['recruiter_id']

    status, candidate_login = call('POST', '/login', {
        'email': candidate_email,
        'password': password,
        'role': 'candidate'
    })
    assert status == 200, f'Candidate login failed: {status} {candidate_login}'

    status, recruiter_login = call('POST', '/login', {
        'email': recruiter_email,
        'password': password,
        'role': 'recruiter'
    })
    assert status == 200, f'Recruiter login failed: {status} {recruiter_login}'

    candidate_id = candidate_login['user']['candidate_id']
    recruiter_id = recruiter_login['user']['recruiter_id']

    job_title = f'Auth Verified Job {suffix}'
    status, job_resp = call('POST', '/jobs', {
        'title': job_title,
        'department': 'Platform',
        'location': 'Remote',
        'recruiter_id': recruiter_id
    })
    assert status == 201, f'Job post failed: {status} {job_resp}'
    job_id = job_resp['job_id']

    status, apply_resp = call('POST', '/apply', {
        'job_id': job_id,
        'candidate_id': candidate_id
    })
    assert status == 201, f'Apply failed: {status} {apply_resp}'
    application_id = apply_resp['application_id']

    status, candidate_apps = call('GET', f'/applications/candidate/{candidate_id}')
    assert status == 200, f'Candidate applications endpoint failed: {status} {candidate_apps}'
    assert any(app['application_id'] == application_id for app in candidate_apps), 'Application missing from candidate applications feed'

    status, upd_resp = call('PUT', f'/applications/{application_id}/status', {
        'status': 'Interviewing'
    })
    assert status == 200, f'Status update failed: {status} {upd_resp}'

    conn = get_db_connection()
    assert conn is not None, 'DB connection failed'

    cur = conn.cursor(dictionary=True)
    cur.execute('SELECT candidate_id, password_hash FROM Candidates WHERE email = %s', (candidate_email,))
    user_candidate = cur.fetchone()
    cur.execute('SELECT recruiter_id, password_hash FROM Recruiters WHERE email = %s', (recruiter_email,))
    user_recruiter = cur.fetchone()
    cur.execute('SELECT status FROM Applications WHERE application_id = %s', (application_id,))
    app_row = cur.fetchone()

    assert user_candidate and user_candidate['candidate_id'] == candidate_id, 'Candidate row missing'
    assert user_recruiter and user_recruiter['recruiter_id'] == recruiter_id, 'Recruiter row missing'
    assert user_candidate['password_hash'], 'Candidate password hash missing'
    assert user_recruiter['password_hash'], 'Recruiter password hash missing'
    assert app_row and app_row['status'] == 'Interviewing', f'Unexpected application status: {app_row}'

    cur.execute('DELETE FROM Applications WHERE application_id = %s', (application_id,))
    cur.execute('DELETE FROM Jobs WHERE job_id = %s', (job_id,))
    cur.execute('DELETE FROM Candidates WHERE email = %s', (candidate_email,))
    cur.execute('DELETE FROM Recruiters WHERE email = %s', (recruiter_email,))
    conn.commit()

    cur.close()
    conn.close()

    print('AUTH + WORKFLOW PASS')
    print(json.dumps({
        'candidate_email': candidate_email,
        'recruiter_email': recruiter_email,
        'candidate_id': candidate_id,
        'recruiter_id': recruiter_id,
        'job_id': job_id,
        'application_id': application_id,
        'final_status': 'Interviewing',
        'cleanup': 'done'
    }, indent=2))


if __name__ == '__main__':
    main()
