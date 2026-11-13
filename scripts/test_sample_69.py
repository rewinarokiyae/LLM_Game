from app.security.authentication import AuthenticationService
from app.nlp.query_router import QueryRouter

admin_user = AuthenticationService.authenticate_demo("admin")
sample_qs = [
    "How many teaching hours does FAC001 have for the week starting 2026-11-09?",
    "Which faculty member has the highest teaching workload?",
    "Which faculty members in DEP-CSE exceed their policy limits?",
    "What is Dr. Meera Nair's approved weekly workload relief?",
    "Which faculty member has approved medical leave on 2026-11-12?",
    "How many assignments are assigned to Dr. Meera Nair?",
    "Do laboratory hours count towards teaching workload?",
    "Which subject has ID CS501?",
    "What is the salary of Dr. Meera Nair?"
]

for q in sample_qs:
    res = QueryRouter.process_query(admin_user, q)
    print(f"Q: {q}")
    print(f"INTENT: {res.get('intent')}")
    resp = res.get('response', '')
    print(f"RESP: {resp[:120].strip()}...\n")

