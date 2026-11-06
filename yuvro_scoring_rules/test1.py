import os
import sys
import traceback


def _ensure_django():
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
            try:
                django.setup()
            except Exception:
                for mod in ('todo.settings', 'config.settings', 'myproject.settings', 'app.settings'):
                    try:
                        os.environ['DJANGO_SETTINGS_MODULE'] = mod
                        django.setup()
                        return True
                    except Exception:
                        continue
                return False
        return True
    except Exception:
        return False


def _find_registration_endpoint():
    """Try to discover a registration URL from the URLconf."""
    candidates = [
        '/api/register/',
        '/api/signup/',
        '/api/users/register/',
        '/api/auth/register/',
        '/register/',
        '/signup/',
        '/api/users/',
        '/users/register/',
        '/api/accounts/register/',
        '/accounts/register/',
    ]
    try:
        from django.urls import get_resolver
        resolver = get_resolver()
        found = []

        def walk(patterns, prefix=''):
            for p in patterns:
                try:
                    pat = prefix + str(p.pattern)
                except Exception:
                    continue
                if hasattr(p, 'url_patterns'):
                    walk(p.url_patterns, pat)
                else:
                    name = getattr(p, 'name', None) or ''
                    if any(k in pat.lower() for k in ('register', 'signup', 'sign-up')) or \
                       any(k in name.lower() for k in ('register', 'signup')):
                        found.append('/' + pat.lstrip('/'))
        walk(resolver.url_patterns)
        if found:
            return found
    except Exception:
        pass
    return candidates


def _get_serializer():
    """Try to import a registration serializer from the candidate app."""
    candidates = [
        ('accounts.serializers', 'UserRegistrationSerializer'),
        ('users.serializers', 'UserRegistrationSerializer'),
        ('authentication.serializers', 'UserRegistrationSerializer'),
        ('todo.serializers', 'UserRegistrationSerializer'),
        ('api.serializers', 'UserRegistrationSerializer'),
        ('accounts.serializers', 'RegisterSerializer'),
        ('users.serializers', 'RegisterSerializer'),
        ('authentication.serializers', 'RegisterSerializer'),
        ('todo.serializers', 'RegisterSerializer'),
        ('api.serializers', 'RegisterSerializer'),
        ('accounts.serializers', 'RegistrationSerializer'),
        ('users.serializers', 'RegistrationSerializer'),
        ('todo.serializers', 'RegistrationSerializer'),
        ('api.serializers', 'RegistrationSerializer'),
    ]
    for mod_name, cls_name in candidates:
        try:
            mod = __import__(mod_name, fromlist=[cls_name])
            cls = getattr(mod, cls_name, None)
            if cls is not None:
                return cls
        except Exception:
            continue
    return None


def _cleanup_users(emails):
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for email in emails:
            try:
                User.objects.filter(email__iexact=email).delete()
            except Exception:
                pass
    except Exception:
        pass


def _run_serializer_checks():
    """Validate via the registration serializer directly."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    serializer_cls = _get_serializer()
    if serializer_cls is None:
        return None

    base_email = 'yuvro_dup_test_%s@example.com' % os.getpid()
    upper_email = base_email.upper()
    username1 = 'yuvro_u1_%s' % os.getpid()
    username2 = 'yuvro_u2_%s' % os.getpid()
    username3 = 'yuvro_u3_%s' % os.getpid()

    try:
        # First registration should succeed
        s1 = serializer_cls(data={
            'username': username1,
            'email': base_email,
            'password': 'StrongPass!123',
        })
        if not s1.is_valid():
            return {
                'result': 'failed',
                'score': 0,
                'message': 'Valid registration was rejected by serializer: %s' % s1.errors,
            }
        s1.save()

        # Duplicate (exact case) should fail
        s2 = serializer_cls(data={
            'username': username2,
            'email': base_email,
            'password': 'StrongPass!123',
        })
        if s2.is_valid():
            return {
                'result': 'failed',
                'score': 0,
                'message': 'Duplicate email (exact case) was accepted by serializer; expected validation error.',
            }
        errs2 = s2.errors
        if 'email' not in errs2 and 'non_field_errors' not in errs2:
            return {
                'result': 'failed',
                'score': 0,
                'message': 'Duplicate email rejected but no email-specific error returned: %s' % errs2,
            }

        # Duplicate (different case) should fail
        s3 = serializer_cls(data={
            'username': username3,
            'email': upper_email,
            'password': 'StrongPass!123',
        })
        if s3.is_valid():
            return {
                'result': 'failed',
                'score': 0,
                'message': 'Duplicate email with different casing was accepted; case-insensitive uniqueness not enforced.',
            }
        errs3 = s3.errors
        if 'email' not in errs3 and 'non_field_errors' not in errs3:
            return {
                'result': 'failed',
                'score': 0,
                'message': 'Case-insensitive duplicate rejected but no email-specific error returned: %s' % errs3,
            }

        return {
            'result': 'passed',
            'score': 10,
            'message': 'Serializer correctly rejects duplicate emails (case-sensitive and case-insensitive) and accepts valid registrations.',
        }
    finally:
        _cleanup_users([base_email, upper_email])


def _run_api_checks():
    """Validate via HTTP API using Django test client."""
    from django.test import Client
    from django.contrib.auth import get_user_model
    User = get_user_model()

    endpoints = _find_registration_endpoint()
    base_email = 'yuvro_api_dup_%s@example.com' % os.getpid()
    upper_email = base_email.upper()
    username1 = 'yuvro_api_u1_%s' % os.getpid()
    username2 = 'yuvro_api_u2_%s' % os.getpid()
    username3 = 'yuvro_api_u3_%s' % os.getpid()

    client = Client()
    last_error = None

    try:
        for endpoint in endpoints:
            try:
                # Reset state for this endpoint attempt
                _cleanup_users([base_email, upper_email])

                payload1 = {'username': username1, 'email': base_email, 'password': 'StrongPass!123'}
                r1 = client.post(endpoint, data=payload1, content_type='application/json')
                if r1.status_code not in (200, 201):
                    last_error = 'Endpoint %s returned %s for valid registration' % (endpoint, r1.status_code)
                    continue

                payload2 = {'username': username2, 'email': base_email, 'password': 'StrongPass!123'}
                r2 = client.post(endpoint, data=payload2, content_type='application/json')
                if r2.status_code != 400:
                    last_error = 'Endpoint %s returned %s for duplicate email (expected 400)' % (endpoint, r2.status_code)
                    continue

                payload3 = {'username': username3, 'email': upper_email, 'password': 'StrongPass!123'}
                r3 = client.post(endpoint, data=payload3, content_type='application/json')
                if r3.status_code != 400:
                    last_error = 'Endpoint %s returned %s for case-insensitive duplicate (expected 400)' % (endpoint, r3.status_code)
                    continue

                return {
                    'result': 'passed',
                    'score': 10,
                    'message': 'API endpoint %s correctly rejects duplicate emails (case-sensitive and case-insensitive) with 400 and accepts valid registrations.' % endpoint,
                }
            except Exception as e:
                last_error = 'Endpoint %s raised: %s' % (endpoint, e)
                continue

        return {
            'result': 'failed',
            'score': 0,
            'message': 'Could not validate via API. Last error: %s' % (last_error or 'no working registration endpoint found'),
        }
    finally:
        _cleanup_users([base_email, upper_email])


def evaluate():
    try:
        if not _ensure_django():
            return {
                'result': 'failed',
                'score': 0,
                'message': 'Django could not be initialized. Ensure DJANGO_SETTINGS_MODULE is set or a settings module exists.',
            }

        # Prefer serializer-level check (more direct, less dependent on URL routing)
        serializer_result = None
        try:
            serializer_result = _run_serializer_checks()
        except Exception as e:
            serializer_result = {
                'result': 'failed',
                'score': 0,
                'message': 'Serializer check raised: %s' % e,
            }

        if serializer_result is not None and serializer_result.get('result') == 'passed':
            return serializer_result

        # Fall back to API-level check
        try:
            api_result = _run_api_checks()
        except Exception as e:
            api_result = {
                'result': 'failed',
                'score': 0,
                'message': 'API check raised: %s' % e,
            }

        if api_result.get('result') == 'passed':
            return api_result

        # Both failed - report the more informative message
        if serializer_result is not None:
            return serializer_result
        return api_result
    except Exception as e:
        return {
            'result': 'failed',
            'score': 0,
            'message': 'Unexpected error in evaluate(): %s\n%s' % (e, traceback.format_exc()),
        }
