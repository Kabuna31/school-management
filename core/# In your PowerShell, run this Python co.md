# In your PowerShell, run this Python command
python -c "
import psycopg2
import os

# REPLACE with your actual Render database URL
DATABASE_URL = 'postgresql://schooldb_rvpf_user:AjBgGkE0HuTseLPkYIgz58qrlbOkfGfd@dpg-d8rgd9n7f7vs73e1941g-a.oregon-postgres.render.com/schooldb_rvpf'

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\")
    tables = cursor.fetchall()
    print('\n📊 Tables in database:')
    for table in tables:
        print(f'  - {table[0]}')
    
    # Check core tables specifically
    cursor.execute(\"SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'core_%'\")
    core_tables = cursor.fetchall()
    print(f'\n📋 Core tables ({len(core_tables)}):')
    for table in core_tables:
        print(f'  ✅ {table[0]}')
    
    # Check migrations
    cursor.execute(\"SELECT app, name FROM django_migrations ORDER BY app, id\")
    migrations = cursor.fetchall()
    print(f'\n📝 Migrations applied ({len(migrations)}):')
    for app, name in migrations:
        print(f'  - {app}: {name}')
    
    conn.close()
    print('\n✅ Connection successful!')
    
except Exception as e:
    print(f'❌ Error: {e}')
"