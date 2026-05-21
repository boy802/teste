ARQUIVOS PRONTOS PARA RENDER

1. Envie a pasta config para o projeto.
2. Edite br_config.json e coloque seu UID e senha.
3. No Render:
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn wsgi:app

Teste:
https://SEUAPP.onrender.com/like?uid=ID
