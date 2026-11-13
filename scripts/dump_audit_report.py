import json

with open("reports/llm_audit_report.json", "r", encoding="utf-8") as f:
    report = json.load(f)

categories = [
    "Faculty Workload",
    "Department Workload",
    "Workload Policies",
    "Leave Management",
    "Assignment Management",
    "Timetable",
    "Subject Retrieval",
    "Advanced Reasoning",
    "Hallucination Prevention"
]

for cat in categories:
    items = [r for r in report["results"] if r["category_name"] == cat]
    passed = sum(1 for r in items if r["status"] == "PASS")
    print(f"\n=======================================================")
    print(f"CATEGORY: {cat} ({passed}/{len(items)} Passed)")
    print(f"=======================================================")
    for r in items:
        st = r["status"]
        sym = "PASS" if st == "PASS" else ("PARTIAL" if st == "PARTIAL" else st)
        print(f"\n[{sym}] {r['test_id']}: {r['question']}")
        print(f"  Expected: {r['expected_answer'].replace(chr(10), ' ')}")
        act = r['actual_answer'].replace(chr(10), ' ').strip()
        print(f"  Actual  : {act[:100]}...")
        if st != "PASS":
            print(f"  Why     : {r['reason']}")
            print(f"  Issue   : {r['what_went_wrong']}")
            print(f"  Category: {r['failure_category']}")
            print(f"  Fix     : {r['suggested_correction']}")
