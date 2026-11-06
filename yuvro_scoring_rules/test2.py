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


def _find_todos_url():
    from django.urls import get_resolver
    resolver = get_resolver()
    candidates = ['/api/todos/', 'api/todos/', '/todos/', 'todos/']
    for c in candidates:
        try:
            match = resolver.resolve(c)
            if match:
                return c
        except Exception:
            continue
    return '/api/todos/'


def evaluate():
    try:
        _ensure_django()
        from django.test import Client
        from django.contrib.auth.models import User
        from rest_framework.authtoken.models import Token

        created_user = None
        try:
            # Create a test user
            created_user = User.objects.create_user(username='yuvro_todo_user', email='yuvro_todo_user@example.com', password='password123')
            token, _ = Token.objects.get_or_create(user=created_user)

            client = Client()
            url = _find_todos_url()

            # Test 1: unauthenticated request should be rejected (401 or 403)
            resp = client.post(url, data=json.dumps({'title': 'Test todo'}), content_type='application/json')
            if resp.status_code not in (401, 403):
                return {"result": "failed", "score": 0, "message": f"Unauthenticated POST expected 401/403, got {resp.status_code}: {resp.content[:300]}"}

            # Test 2: authenticated valid creation
            auth_header = {'HTTP_AUTHORIZATION': f'Token {token.key}'}
            resp = client.post(url, data=json.dumps({'title': 'My first todo'}), content_type='application/json', **auth_header)
            if resp.status_code not in (200, 201):
                return {"result": "failed", "score": 0, "message": f"Authenticated POST expected 200/201, got {resp.status_code}: {resp.content[:300]}"}

            # Verify ownership
            try:
                from todo.models import Todo
            except Exception:
                try:
                    from todos.models import Todo
                except Exception:
                    try:
                        from api.models import Todo
                    except Exception:
                        Todo = None

            if Todo is not None:
                todo = Todo.objects.filter(title='My first todo').order_by('-id').first()
                if todo is None:
                    return {"result": "failed", "score": 0, "message": "Todo was not created in DB"}
                if getattr(todo, 'user_id', None) != created_user.id:
                    return {"result": "failed", "score": 0, "message": f"Todo not assigned to authenticated user (user_id={getattr(todo, 'user_id', None)})"}

            # Test 3: empty title should be rejected
            resp = client.post(url, data=json.dumps({'title': '   '}), content_type='application/json', **auth_header)
            if resp.status_code != 400:
                return {"result": "failed", "score": 0, "message": f"Empty title expected 400, got {resp.status_code}: {resp.content[:300]}"}

            # Test 4: title too long should be rejected
            long_title = 'x' * 201
            resp = client.post(url, data=json.dumps({'title': long_title}), content_type='application/json', **auth_header)
            if resp.status_code != 400:
                return {"result": "failed", "score": 0, "message": f"Too-long title expected 400, got {resp.status_code}: {resp.content[:300]}"}

            return {"result": "passed", "score": 10, "message": "Authentication, ownership assignment, and title validation all passed"}
        finally:
            try:
                if created_user is not None:
                    try:
                        from todo.models import Todo
                    except Exception:
                        try:
                            from todos.models import Todo
                        except Exception:
                            try:
                                from api.models import Todo
                            except Exception:
                                Todo = None
                    if Todo is not None:
                        Todo.objects.filter(user=created_user).delete()
                    created_user.delete()
            except Exception:
                pass
    except Exception as e:
        tb = traceback.format_exc()
        return {"result": "failed", "score": 0, "message": f"{type(e).__name__}: {e}\n{tb}"}
