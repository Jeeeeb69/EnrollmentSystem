FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD python -c "import os; keys=('DATABASE_URL','DATABASE_PRIVATE_URL','DATABASE_PUBLIC_URL','POSTGRES_URL','POSTGRES_PRIVATE_URL','POSTGRES_PUBLIC_URL','PGDATABASE','PGUSER','PGPASSWORD','PGHOST','POSTGRES_DB','POSTGRES_USER','POSTGRES_PASSWORD','POSTGRES_HOST'); print('Database env keys present=' + ','.join(k for k in keys if os.environ.get(k)))" && python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','enrollment_system.settings'); from django.conf import settings; db=settings.DATABASES['default']; print(f\"Database source={getattr(settings, 'DATABASE_SOURCE', 'unknown')} engine={db.get('ENGINE')} host={db.get('HOST')} name={db.get('NAME')} user={db.get('USER')}\")" && python manage.py migrate --noinput && python manage.py seed_admin && daphne -b 0.0.0.0 -p ${PORT:-8000} enrollment_system.asgi:application
