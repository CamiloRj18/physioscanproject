from app import create_app
import re
app = create_app('desarrollo')
with app.app_context():
    with app.test_client() as c:
        paths = ['/auth/login', '/auth/registro', '/recuperar']
        for path in paths:
            resp = c.get(path)
            body = resp.data.decode('utf-8', errors='ignore')
            emojis = re.compile(r'[\U0001F300-\U0001F9FF]').findall(body)
            has_tokens = 'tokens.css' in body
            has_resp = 'responsive.css' in body
            print(path, resp.status_code, 'tokens=' + str(has_tokens), 'resp=' + str(has_resp), 'emojis=' + str(emojis or 'NINGUNO'))
