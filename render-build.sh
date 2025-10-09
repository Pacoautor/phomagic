# Dentro de la carpeta del proyecto
py -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

# (Opcional) crea un .env para local
# SECRET_KEY de prueba + DEBUG=True y SQLite
# Luego:
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
