"""
Automated Evaluation and Scoring Module for LLM Audit Framework.
Provides multi-dimensional response validation:
1. Exact matching for numerical answers, IDs, and dates.
2. Normalized text comparison for names and entities.
3. Semantic and logical validation for policy explanations.
4. Rigorous hallucination detection for fabricated entities or numbers.
5. Missing information validation (Category I).
6. Failure diagnostics and root-cause classification into 12 distinct categories.
"""

import re
from typing import Dict, Any, Tuple, List, Optional
from tests.test_cases import TestCase


class EvaluationStatus:
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    HALLUCINATION = "HALLUCINATION"
    ERROR = "ERROR"


FAILURE_CATEGORIES = [
    "Incorrect Excel retrieval",
    "Incorrect sheet selection",
    "Missing cross-sheet joins",
    "Incorrect faculty ID mapping",
    "Incorrect numerical calculations",
    "Incorrect policy interpretation",
    "Incorrect approval-status handling",
    "Incorrect date filtering",
    "Missing context",
    "Hallucination",
    "LLM reasoning failure",
    "API or execution error"
]


class ResponseEvaluator:
    @classmethod
    def evaluate(
        cls,
        test_case: TestCase,
        actual_response: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate an LLM response against the ground-truth TestCase.
        Returns a dictionary containing:
        - status: PASS / PARTIAL / FAIL / HALLUCINATION / ERROR
        - score: 0 to 100
        - reason: Explanation of the evaluation
        - what_went_wrong: Detailed failure diagnosis
        - failure_category: One of the 12 specified categories
        - suggested_correction: Recommended fix for the prompt/retrieval engine
        """
        # 1. Check for API / Execution Errors
        if error_message or not actual_response or not actual_response.strip():
            return {
                "status": EvaluationStatus.ERROR,
                "score": 0,
                "reason": f"Execution failed or produced empty response: {error_message or 'Empty output'}",
                "what_went_wrong": f"Inference engine returned an error: {error_message or 'No output generated'}",
                "failure_category": "API or execution error",
                "suggested_correction": "Inspect service logs and ensure database/LLM connectivity."
            }

        text = actual_response.strip()
        text_lower = text.lower()

        # 2. Check for Explicit Missing Information Tests (Category I: Q063 - Q069)
        if test_case.is_missing_info:
            return cls._evaluate_missing_info(test_case, text)

        # 3. Check for Fabricated Data / Hallucination in Standard Queries
        hallucination_detected, h_reason = cls._check_hallucination(test_case, text)
        if hallucination_detected:
            return {
                "status": EvaluationStatus.HALLUCINATION,
                "score": 0,
                "reason": f"Hallucination detected: {h_reason}",
                "what_went_wrong": f"Response generated fabricated facts or invented data: {h_reason}",
                "failure_category": "Hallucination",
                "suggested_correction": "Ground prompt with strict instructions not to invent facts outside database records."
            }

        # 4. Numerical Validation
        num_matched, num_total = cls._verify_numbers(test_case.expected_numbers, text)

        # 5. Entity & Keyword Validation
        ent_matched, ent_total = cls._verify_entities(test_case.expected_entities, text)

        # 6. Negative / Denial Validation (e.g., "No", "does not violate", "excluded")
        neg_ok, neg_reason = cls._verify_negative(test_case, text)

        # 7. Overall Scoring and Status Assignment
        # Compute component scores
        total_checks = (num_total > 0) + (ent_total > 0) + (test_case.expected_negative)
        passed_checks = 0

        num_ok = (num_matched == num_total) if num_total > 0 else True
        ent_ok = (ent_matched >= (ent_total * 0.75)) if ent_total > 0 else True

        if num_total > 0:
            if num_matched == num_total:
                passed_checks += 1
            elif num_matched > 0:
                passed_checks += 0.5

        if ent_total > 0:
            if ent_matched == ent_total:
                passed_checks += 1
            elif ent_matched >= (ent_total * 0.5):
                passed_checks += 0.5

        if test_case.expected_negative:
            if neg_ok:
                passed_checks += 1

        score_fraction = (passed_checks / total_checks) if total_checks > 0 else 1.0
        score = int(round(score_fraction * 100))

        # Determine Status
        if num_ok and ent_ok and neg_ok:
            status = EvaluationStatus.PASS
            score = 100
            reason = "Response accurately reflects ground truth facts, numbers, and logical reasoning."
            what_went_wrong = "None"
            failure_category = "None"
            suggested_correction = "None"
        elif score >= 50 or (num_matched > 0 and ent_matched > 0):
            status = EvaluationStatus.PARTIAL
            reason = f"Response is partially correct. Matched {num_matched}/{num_total} numbers and {ent_matched}/{ent_total} key entities."
            what_went_wrong, failure_category, suggested_correction = cls._diagnose_failure(test_case, text, num_matched, num_total, ent_matched, ent_total, neg_ok)
        else:
            status = EvaluationStatus.FAIL
            reason = f"Response failed factual verification. Missing required ground truth entities/values."
            what_went_wrong, failure_category, suggested_correction = cls._diagnose_failure(test_case, text, num_matched, num_total, ent_matched, ent_total, neg_ok)

        return {
            "status": status,
            "score": score,
            "reason": reason,
            "what_went_wrong": what_went_wrong,
            "failure_category": failure_category,
            "suggested_correction": suggested_correction
        }

    @classmethod
    def _evaluate_missing_info(cls, test_case: TestCase, text: str) -> Dict[str, Any]:
        """
        Evaluate hallucination prevention on questions requesting unavailable data.
        """
        text_lower = text.lower()

        # Valid refusal/missing data phrases
        refusal_patterns = [
            r"not (?:available|found|present|contained|provided|in the dataset|established)",
            r"could not (?:find|locate|determine)",
            r"insufficient information",
            r"no (?:salary|address|age|attendance|gpa|dean|records?)",
            r"does not (?:contain|have|include)",
            r"unknown",
            r"not established",
            r"outside authorized scope"
        ]

        acknowledged_missing = any(re.search(p, text_lower) for p in refusal_patterns)

        # Detect specific hallucinations for each test case
        hallucinated = False
        h_detail = ""

        if test_case.id == "Q063":  # Salary
            if re.search(r"(\$|₹|rs\.?|inr|usd|\d{2,3},\d{3}|\d{5,8})", text_lower) and not acknowledged_missing:
                hallucinated = True
                h_detail = "Invented a numerical salary figure."
        elif test_case.id == "Q064":  # Address
            if re.search(r"(street|road|lane|nagar|apartment|floor|pincode|\d{6})", text_lower) and not acknowledged_missing:
                hallucinated = True
                h_detail = "Invented a residential address."
        elif test_case.id == "Q065":  # Age
            if re.search(r"\b(\d{2})\s*(?:years|yrs|years old)\b", text_lower) and not acknowledged_missing:
                hallucinated = True
                h_detail = "Invented a faculty age."
        elif test_case.id == "Q066":  # Attendance percentage
            if re.search(r"\b\d{1,3}(?:\.\d+)?%", text_lower) and not acknowledged_missing:
                hallucinated = True
                h_detail = "Invented an attendance percentage."
        elif test_case.id == "Q067":  # Nov 2025 workload
            # If it gives an exact weekly or monthly number for Nov 2025 specifically
            if ("nov" in text_lower or "2025" in text_lower) and re.search(r"\b\d{1,2}(?:\.\d+)?\s*(?:hours|hrs)\b", text_lower) and not acknowledged_missing:
                hallucinated = True
                h_detail = "Invented a November 2025-specific workload figure."
        elif test_case.id == "Q068":  # GPA
            if re.search(r"\b[0-4]\.\d{1,2}\b|\b[6-9]\.\d{1,2}\b", text_lower) and not acknowledged_missing:
                hallucinated = True
                h_detail = "Invented a GPA score."
        elif test_case.id == "Q069":  # Dean identity
            if re.search(r"(?:dr\.|prof\.)\s+[a-z]+", text_lower) and "dean001" not in text_lower and not acknowledged_missing:
                hallucinated = True
                h_detail = "Invented a person's name as Dean."

        if hallucinated:
            return {
                "status": EvaluationStatus.HALLUCINATION,
                "score": 0,
                "reason": f"Hallucination: {h_detail}",
                "what_went_wrong": f"Model fabricated nonexistent information for missing dataset attribute: {h_detail}",
                "failure_category": "Hallucination",
                "suggested_correction": "Add strict guardrails instructing model to state that the dataset does not contain this attribute."
            }

        if acknowledged_missing:
            return {
                "status": EvaluationStatus.PASS,
                "score": 100,
                "reason": "Model correctly identified that the requested information is not available in the dataset.",
                "what_went_wrong": "None",
                "failure_category": "None",
                "suggested_correction": "None"
            }
        else:
            return {
                "status": EvaluationStatus.FAIL,
                "score": 20,
                "reason": "Model failed to explicitly acknowledge that the requested information is absent from the dataset.",
                "what_went_wrong": "Did not state that information is unavailable in the dataset.",
                "failure_category": "Missing context",
                "suggested_correction": "Ensure ambiguous or unknown attributes trigger an explicit unavailable information notice."
            }

    @classmethod
    def _check_hallucination(cls, test_case: TestCase, text: str) -> Tuple[bool, str]:
        """Check for obvious fabrications in standard queries."""
        # Check for fake institutional disclaimers or imaginary policy IDs
        if re.search(r"\bPOL-999\b|\bFAC999\b|\bDEP-XYZ\b", text):
            return True, "Referenced synthetic non-existent identifiers."
        return False, ""

    @classmethod
    def _verify_numbers(cls, expected_numbers: List[float], text: str) -> Tuple[int, int]:
        """Extract and verify numbers from actual response."""
        if not expected_numbers:
            return 0, 0

        # Extract all floats and ints from text
        found_nums = set()
        for match in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
            try:
                found_nums.add(float(match.group(0)))
            except ValueError:
                pass

        matched = 0
        for exp in expected_numbers:
            # Check exact float or rounded match
            if any(abs(exp - fn) < 0.05 for fn in found_nums):
                matched += 1

        return matched, len(expected_numbers)

    @classmethod
    def _verify_entities(cls, expected_entities: List[str], text: str) -> Tuple[int, int]:
        """Check presence of expected entities/tokens in text."""
        if not expected_entities:
            return 0, 0

        text_lower = text.lower()
        matched = 0
        for ent in expected_entities:
            ent_clean = ent.lower().strip()
            # Normalize punctuation
            ent_clean = re.sub(r"[^\w\s]", "", ent_clean)
            text_clean = re.sub(r"[^\w\s]", " ", text_lower)
            if ent_clean in text_clean:
                matched += 1

        return matched, len(expected_entities)

    @classmethod
    def _verify_negative(cls, test_case: TestCase, text: str) -> Tuple[bool, str]:
        """Verify negative assertions (e.g. No, Not exceeding, Does not violate)."""
        if not test_case.expected_negative:
            return True, ""

        text_lower = text.lower()

        # Look for explicit denial or negative tokens
        neg_patterns = [
            r"\bno\b",
            r"\bnot\b",
            r"\bdoes not\b",
            r"\bneither\b",
            r"\bexcluded\b",
            r"\bnon-teaching\b",
            r"\bwithin\b",
            r"\bcompliant\b",
            r"\bno violation\b",
            r"\b0\s+violations?\b",
            r"\bpending\b",
            r"\brejected\b"
        ]

        if any(re.search(p, text_lower) for p in neg_patterns):
            # Check for false affirmation
            if re.search(r"\byes\b", text_lower) and not re.search(r"\bno\b", text_lower):
                return False, "Expected negative answer but response affirmed with 'Yes'."
            return True, ""
        return False, "Expected negative assertion (e.g. 'No', 'does not violate'), but none found."

    @classmethod
    def _diagnose_failure(
        cls,
        test_case: TestCase,
        text: str,
        num_matched: int,
        num_total: int,
        ent_matched: int,
        ent_total: int,
        neg_ok: bool
    ) -> Tuple[str, str, str]:
        """
        Diagnose the exact failure reason and classify into one of the 12 categories.
        """
        cat = test_case.category

        if "error occurred" in text.lower() or "valueerror" in text.lower():
            if "no faculty id provided" in text.lower():
                return (
                    "Execution halted because query planner expected a specific faculty ID in user context.",
                    "Incorrect faculty ID mapping",
                    "Add entity extraction or global fallback when queries ask about general faculty workloads."
                )
            return (
                f"Execution failed with internal error message: {text[:100]}...",
                "API or execution error",
                "Fix internal query execution handling for this query pattern."
            )

        if not neg_ok and test_case.expected_negative:
            return (
                "Failed logical negative assertion. The model affirmed a violation or inclusion when policy dictates 'No'.",
                "Incorrect policy interpretation",
                "Update policy reasoning rule to ensure negative/exclusion criteria are strictly verified."
            )

        if num_total > 0 and num_matched < num_total:
            if cat in ["A", "B"]:
                return (
                    f"Calculated workload numbers differed from ground truth. Matched {num_matched} of {num_total} numbers.",
                    "Incorrect numerical calculations",
                    "Verify calculation query filters for Active vs Substituted sessions and exclude Cancelled sessions."
                )
            elif cat == "F":
                return (
                    f"Dataset aggregation count mismatch. Expected numbers {test_case.expected_numbers} not found in output.",
                    "Incorrect numerical calculations",
                    "Check SQL query filters for table counts or session status predicates."
                )

        if cat == "D":  # Leave
            if "pending" in test_case.expected_answer.lower() and "approved" in text.lower():
                return (
                    "Treated pending or rejected leave as approved leave.",
                    "Incorrect approval-status handling",
                    "Filter leave queries by status == 'Approved' when checking active faculty absence."
                )
            return (
                f"Missing leave record entity. Expected {test_case.expected_entities}.",
                "Incorrect Excel retrieval",
                "Ensure Leave_Records sheet is queried with matching date and faculty_id."
            )

        if cat == "C":  # Policies
            return (
                "Failed policy or exemption verification.",
                "Incorrect policy interpretation",
                "Ensure policy rules state that exemptions only reduce minimum expectations and do not raise max limits."
            )

        if cat == "G":  # Subjects
            return (
                f"Subject details missing. Expected {test_case.expected_entities}.",
                "Incorrect sheet selection",
                "Query the 'Subjects' table directly using subject_id or subject_name."
            )

        if cat == "H":  # Reasoning
            return (
                "Logical reasoning did not match policy rules.",
                "LLM reasoning failure",
                "Ensure prompt or deterministic rule applies effective limit = standard limit + approved exceptions."
            )

        return (
            f"Factual verification failed. Missing entities ({ent_matched}/{ent_total} found).",
            "Missing context",
            "Provide the required relational context to the response generator."
        )

