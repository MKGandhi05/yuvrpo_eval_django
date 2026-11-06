import os
import sys
import json
import traceback


def _setup_django():
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
            try:
                django.setup()
            except Exception:
                # Fallback: try common settings modules
                for mod in ('todo.settings', 'config.settings', 'myproject.settings', 'app.settings'):
                    try:
                        os.environ['DJANGO_SETTINGS_MODULE'] = mod
                        django.setup()
                        break
                    except Exception:
                        continue
    except Exception:
        pass


def _load_evaluator(module_name):
    try:
        mod = __import__(module_name, fromlist=['evaluate'])
        return getattr(mod, 'evaluate')
    except Exception as e:
        def _err(_e=e):
            return {
                'result': 'failed',
                'score': 0,
                'message': 'Failed to import evaluator %s: %s' % (module_name, _e),
            }
        return _err


def main():
    _setup_django()

    # Ensure the scoring rules directory is importable
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    tasks = {}
    max_possible = 0

    task_specs = [
        ('task1', 'test1', 10),
    ]

    for task_key, module_name, marks in task_specs:
        max_possible += marks
        evaluate = _load_evaluator(module_name)
        try:
            result = evaluate()
            if not isinstance(result, dict):
                result = {
                    'result': 'failed',
                    'score': 0,
                    'message': 'Evaluator returned non-dict result: %r' % (result,),
                }
            # Normalize
            res = result.get('result', 'failed')
            if res not in ('passed', 'failed'):
                res = 'failed'
            score = result.get('score', 0)
            try:
                score = int(score)
            except Exception:
                score = 0
            if res == 'failed':
                score = 0
            if score < 0:
                score = 0
            if score > marks:
                score = marks
            msg = result.get('message', '')
            if not isinstance(msg, str):
                msg = str(msg)
            tasks[task_key] = {
                'result': res,
                'score': score,
                'message': msg,
            }
        except Exception as e:
            tasks[task_key] = {
                'result': 'failed',
                'score': 0,
                'message': 'Unhandled exception in evaluator: %s\n%s' % (e, traceback.format_exc()),
            }

    total = sum(t['score'] for t in tasks.values())
    output = {
        'tasks': tasks,
        'total_score': total,
        'max_possible_score': max_possible,
    }
    sys.stdout.write(json.dumps(output))
    sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        fallback = {
            'tasks': {
                'task1': {
                    'result': 'failed',
                    'score': 0,
                    'message': 'Fatal runner error: %s' % e,
                }
            },
            'total_score': 0,
            'max_possible_score': 10,
        }
        sys.stdout.write(json.dumps(fallback))
        sys.stdout.write('\n')
        sys.stdout.flush()
