# 1 - SETUP DE LA BD

### 1. Créer le user
CREATE USER todo_db_user WITH PASSWORD 'ton_mot_de_passe';

### 2. Créer la BD avec ce user comme owner
CREATE DATABASE todo OWNER todo_db_user;

### 3. Se connecter à la BD
\c todo

### 4. Droits sur le schema public (obligatoire PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO todo_db_user;

# 2 CREER LE JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# 3 Migration with alembic
alembic init -t async migrations 

alembic revision --autogenerate -m "init"