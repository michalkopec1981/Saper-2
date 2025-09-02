release: sleep 5 && flask init-db
web: gunicorn --worker-class gevent -w 1 --log-file - app:app
