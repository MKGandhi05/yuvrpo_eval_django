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


def _get_todo_model():
    for modpath in ('todo.models', 'todos.models', 'api.models'):
        try:
            mod = __import__(modpath, fromlist=['Todo'])
            if hasattr(mod, 'Todo'):
                return mod.Todo
        except Exception:
            continue
    return None


def evaluate():
    try:
        _ensure_django()
        from django.test import Client
        from django.contrib.auth.models import User
        from rest_framework.authtoken.models import Token

        Todo = _get_todo_model()
        if Todo is None:
            return {"result": "failed", "score": 0, "message": "Could not locate Todo model"}

        user_a = None
        user_b = None
        try:
            user_a = User.objects.create_user(username='yuvro_list_user_a', email='yuvro_list_a@example.com', password='password123')
            user_b = User.objects.create_user(username='yuvro_list_user_b', email='yuvro_list_b@example.com', password='password123')
            token_a, _ = Token.objects.get_or_create(user=user_a)

            # Create 15 todos for user A, 3 for user B
            for i in range(15):
                Todo.objects.create(title=f'UserA todo {i}', user=user_a)
            for i in range(3):
                Todo.objects.create(title=f'UserB todo {i}', user=user_b)

            client = Client()
            url = _find_todos_url()
            auth_header = {'HTTP_AUTHORIZATION': f'Token {token_a.key}'}

            # Test 1: unauthenticated should be rejected
            resp = client.get(url)
            if resp.status_code not in (401, 403):
                return {"result": "failed", "score": 0, "message": f"Unauthenticated GET expected 401/403, got {resp.status_code}: {resp.content[:300]}"}

            # Test 2: authenticated paginated response
            resp = client.get(url, **auth_header)
            if resp.status_code != 200:
                return {"result": "failed", "score": 0, "message": f"Authenticated GET expected 200, got {resp.status_code}: {resp.content[:300]}"}

            try:
                data = json.loads(resp.content.decode('utf-8'))
            except Exception as e:
                return {"result": "failed", "score": 0, "message": f"Response is not valid JSON: {e}"}

            for key in ('count', 'next', 'previous', 'results'):
                if key not in data:
                    return {"result": "failed", "score": 0, "message": f"Paginated response missing key '{key}'. Got keys: {list(data.keys())}"}

            if data.get('count') != 15:
                return {"result": "failed", "score": 0, "message": f"Expected count=15 for user A, got {data.get('count')}"}

            results = data.get('results', [])
            if len(results) != 10:
                return {"result": "failed", "score": 0, "message": f"Expected page size 10, got {len(results)} results"}

            # Ensure only user A's todos are returned
            for item in results:
                title = item.get('title', '')
                if title.startswith('UserB'):
                    return {"result": "failed", "score": 0, "message": f"Response leaked another user's todo: {title}"}

            # Test 3: page 2
            resp2 = client.get(url + '?page=2', **auth_header)
            if resp2.status_code != 200:
                return {"result": "failed", "score": 0, "message": f"Page 2 expected 200, got {resp2.status_code}: {resp2.content[:300]}"}
            data2 = json.loads(resp2.content.decode('utf-8'))
            if len(data2.get('results', [])) != 5:
                return {"result": "failed", "score": 0, "message": f"Page 2 expected 5 results, got {len(data2.get('results', []))}"}

            return {"result": "passed", "score": 10, "message": "Pagination (page size 10), user isolation, and response structure all passed"}
        finally:
            try:
                if user_a is not None:
                    Todo.objects.filter(user=user_a).delete()
                    user_a.delete()
                if user_b is not None:
                    Todo.objects.filter(user=user_b).delete()
                    user_b.delete()
            except Exception:
                pass
    except Exception as e:
        tb = traceback.format_exc()
        return {"result": "failed", "score": 0, "message": f"{type(e).__name__}: {e}\n{tb}"}
