import json

with open("reports/llm_audit_report.json", "r", encoding="utf-8") as f:
    report = json.load(f)

failures = [r for r in report["results"] if r["status"] != "PASS"]
print(f"Total non-passing questions: {len(failures)} / {len(report['results'])}")

categories = {}
for r in failures:
    fc = r["failure_category"]
    categories.setdefault(fc, []).append(r)

for fc, items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"\n=======================================================")
    print(f"FAILURE CATEGORY: {fc} ({len(items)} questions)")
    print(f"=======================================================")
    for item in items:
        print(f"• [{item['status']}] {item['test_id']}: {item['question']}")
        print(f"    Expected: {item['expected_answer'][:80]}...")
        act = item['actual_answer'].replace('\n', ' ')[:80]
        print(f"    Actual  : {act}...")
        print(f"    Issue   : {item['what_went_wrong']}")
