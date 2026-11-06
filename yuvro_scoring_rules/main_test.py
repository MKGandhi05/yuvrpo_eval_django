import os
import sys
import json
import traceback

# Ensure project root is on sys.path so Django settings can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')


def _setup_django():
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            # Try common settings modules
            for mod in ('settings', 'todo_project.settings', 'project.settings', 'config.settings'):
                try:
                    __import__(mod)
                    os.environ['DJANGO_SETTINGS_MODULE'] = mod
                    break
                except Exception:
                    continue
        django.setup()
        return True, None
    except Exception as e:
        return False, str(e)


def _run_task(module_name, task_key, max_score):
    try:
        mod = __import__(module_name, fromlist=['evaluate'])
        result = mod.evaluate()
        if not isinstance(result, dict):
            return {"result": "failed", "score": 0, "message": "evaluate() did not return a dict"}
        res = result.get('result', 'failed')
        score = result.get('score', 0)
        message = result.get('message', '')
        if res not in ('passed', 'failed'):
            res = 'failed'
        try:
            score = int(score)
        except Exception:
            score = 0
        if score < 0:
            score = 0
        if score > max_score:
            score = max_score
        return {"result": res, "score": score, "message": str(message)}
    except Exception as e:
        tb = traceback.format_exc()
        return {"result": "failed", "score": 0, "message": f"{type(e).__name__}: {e}\n{tb}"}


def main():
    tasks = {}
    max_scores = {
        'task1': 10,
        'task2': 10,
        'task3': 10,
    }

    ok, err = _setup_django()
    if not ok:
        # Still attempt to run tests; they will report failures individually
        pass

    # Import test modules relative to this package
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    for task_key in ('task1', 'task2', 'task3'):
        tasks[task_key] = _run_task(task_key, task_key, max_scores[task_key])

    total = sum(t['score'] for t in tasks.values())
    max_possible = sum(max_scores.values())

    output = {
        "tasks": tasks,
        "total_score": total,
        "max_possible_score": max_possible,
    }
    print(json.dumps(output))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        tb = traceback.format_exc()
        fallback = {
            "tasks": {
                "task1": {"result": "failed", "score": 0, "message": f"runner error: {e}"},
                "task2": {"result": "failed", "score": 0, "message": f"runner error: {e}"},
                "task3": {"result": "failed", "score": 0, "message": f"runner error: {e}"},
            },
            "total_score": 0,
            "max_possible_score": 30,
        }
        print(json.dumps(fallback))
