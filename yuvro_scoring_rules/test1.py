import os
import sys
import json
import traceback

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')


def _ensure_django():
    import django
    from django.conf import settings
    if not settings.configured:
        for mod in ('settings', 'todo_project.settings', 'project.settings', 'config.settings'):
            try:
                __import__(mod)
                os.environ['DJANGO_SETTINGS_MODULE'] = mod
                break
            except Exception:
                continue
    django.setup()


def _find_signup_url():
    from django.urls import get_resolver
    resolver = get_resolver()
    candidates = ['/api/signup/', 'api/signup/', '/signup/', 'signup/']
    for c in candidates:
        try:
            match = resolver.resolve(c)
            if match:
                return c
        except Exception:
            continue
    return '/api/signup/'


def evaluate():
    try:
        _ensure_django()
        from django.test import Client
        from django.contrib.auth.models import User
        from django.db import connection

        created_emails = []
        try:
            client = Client()
            url = _find_signup_url()

            # Test 1: valid signup
            email1 = 'yuvro_test_valid_1@example.com'
            created_emails.append(email1)
            resp = client.post(url, data=json.dumps({'email': email1, 'password': 'password123'}), content_type='application/json')
            if resp.status_code not in (200, 201):
                return {"result": "failed", "score": 0, "message": f"Valid signup expected 200/201, got {resp.status_code}: {resp.content[:300]}"}
            if not User.objects.filter(email__iexact=email1).exists():
                return {"result": "failed", "score": 0, "message": "User was not created in DB after valid signup"}

            # Test 2: duplicate email (case-insensitive)
            dup_email = email1.upper()
            resp = client.post(url, data=json.dumps({'email': dup_email, 'password': 'password123'}), content_type='application/json')
            if resp.status_code != 400:
                return {"result": "failed", "score": 0, "message": f"Duplicate email expected 400, got {resp.status_code}: {resp.content[:300]}"}

            # Test 3: weak password (too short)
            email2 = 'yuvro_test_weak_short@example.com'
            created_emails.append(email2)
            resp = client.post(url, data=json.dumps({'email': email2, 'password': 'abc1'}), content_type='application/json')
            if resp.status_code != 400:
                return {"result": "failed", "score": 0, "message": f"Short password expected 400, got {resp.status_code}: {resp.content[:300]}"}
            if User.objects.filter(email__iexact=email2).exists():
                return {"result": "failed", "score": 0, "message": "User was created despite weak (short) password"}

            # Test 4: weak password (no digit)
            email3 = 'yuvro_test_weak_nodigit@example.com'
            created_emails.append(email3)
            resp = client.post(url, data=json.dumps({'email': email3, 'password': 'abcdefgh'}), content_type='application/json')
            if resp.status_code != 400:
                return {"result": "failed", "score": 0, "message": f"Password without digit expected 400, got {resp.status_code}: {resp.content[:300]}"}
            if User.objects.filter(email__iexact=email3).exists():
                return {"result": "failed", "score": 0, "message": "User was created despite password without digit"}

            # Test 5: missing fields
            resp = client.post(url, data=json.dumps({'email': ''}), content_type='application/json')
            if resp.status_code != 400:
                return {"result": "failed", "score": 0, "message": f"Missing password expected 400, got {resp.status_code}: {resp.content[:300]}"}

            return {"result": "passed", "score": 10, "message": "Signup validation, duplicate email handling, and password strength checks all passed"}
        finally:
            try:
                User.objects.filter(email__in=created_emails).delete()
            except Exception:
                pass
            try:
                User.objects.filter(email__iexact='yuvro_test_valid_1@example.com').delete()
            except Exception:
                pass
    except Exception as e:
        tb = traceback.format_exc()
        return {"result": "failed", "score": 0, "message": f"{type(e).__name__}: {e}\n{tb}"}
