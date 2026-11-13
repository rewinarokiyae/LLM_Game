import os

dirs = [
    'app',
    'app/config',
    'app/ingestion',
    'app/database',
    'app/database/repositories',
    'app/database/migrations',
    'app/security',
    'app/llm',
    'app/nlp',
    'app/rag',
    'app/services',
    'app/engines',
    'app/tools',
    'app/response',
    'app/audit',
    'app/cli',
    'app/evaluation',
    'tests',
    'storage/database',
    'storage/vector_store',
    'storage/documents',
    'reports/data_quality',
    'reports/evaluation',
    'logs'
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    if d.startswith('app') or d == 'tests':
        init_file = os.path.join(d, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write('"""Module package initialization."""\n')

print("All directories and __init__.py files initialized successfully.")

