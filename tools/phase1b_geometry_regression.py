#!/usr/bin/env python3
"""Check host-road geometry regressions and independent-readiness separately."""

import argparse
import json
from pathlib import Path
import sys

from phase1b_calibrated_geometry import compare, digest


STATUSES = ("PASS", "FAIL", "INCONCLUSIVE")
ROLES = ("fit", "adaptation", "check")
EPSILON = 0.000001


def combine(statuses):
    if "FAIL" in statuses:
        return "FAIL"
    if "INCONCLUSIVE" in statuses:
        return "INCONCLUSIVE"
    return "PASS"


def unknown_case(case_id, reason):
    return {"id": case_id, "regression_status": "INCONCLUSIVE",
            "decision_status": "INCONCLUSIVE",
            "role_status": {role: "INCONCLUSIVE" for role in ROLES},
            "reasons": [reason]}


def evaluate_case(expected, actual, limits):
    if actual["evidence_sha256"] != expected["evidence_sha256"]:
        return unknown_case(expected["id"], "arcade evidence hash changed")
    observed = actual["role_metrics"]
    role_status = {}
    reasons = []
    for role in ROLES:
        metric = observed.get(role)
        if metric is None:
            role_status[role] = "INCONCLUSIVE"
            continue
        limit = limits[role]
        if metric["count"] < limit["min_rows"]:
            role_status[role] = "INCONCLUSIVE"
            reasons.append(f"{role}: too few rows")
        elif (metric["mean_absolute_edge_error"] > limit["max_mean_edge"] + EPSILON
              or metric["mean_absolute_width_error"] > limit["max_mean_width"] + EPSILON):
            role_status[role] = "FAIL"
            reasons.append(f"{role}: acceptance limit exceeded")
        else:
            role_status[role] = "PASS"
    regression_roles = []
    for role, baseline in expected["baseline_metrics"].items():
        current = observed.get(role)
        if current is None or current["count"] != baseline["count"]:
            regression_roles.append("INCONCLUSIVE")
            reasons.append(f"{role}: missing or changed baseline row count")
        elif (current["mean_absolute_edge_error"] >
              baseline["mean_absolute_edge_error"] + EPSILON or
              current["mean_absolute_width_error"] >
              baseline["mean_absolute_width_error"] + EPSILON):
            regression_roles.append("FAIL")
            reasons.append(f"{role}: worse than recorded baseline")
        else:
            regression_roles.append("PASS")
    return {"id": expected["id"],
            "regression_status": combine(regression_roles),
            "decision_status": combine((role_status["fit"], role_status["check"])),
            "role_status": role_status, "reasons": reasons,
            "role_metrics": observed,
            "host_image_sha256": actual["host_image_sha256"]}


def evaluate(root, criteria_path, comparison_path):
    criteria = json.loads(criteria_path.read_text())
    assert criteria["schema"] == 1
    assert criteria["scope"] == "retrospective_host_geometry_guardrails_not_hardware_acceptance"
    repository = Path(__file__).resolve().parents[1]
    report = {"schema": 1, "criteria_sha256": digest(criteria_path),
              "comparison_sha256": None, "regression_status": "INCONCLUSIVE",
              "decision_status": "INCONCLUSIVE", "reasons": [], "cases": []}
    expected = criteria["cases"]
    assert expected and len({item["id"] for item in expected}) == len(expected)
    try:
        calibration = (repository / criteria["calibration_path"]).resolve()
        cases = (repository / criteria["cases_path"]).resolve()
        assert calibration.is_relative_to(repository) and cases.is_relative_to(repository)
        assert digest(calibration) == criteria["calibration_sha256"]
        assert digest(cases) == criteria["cases_sha256"]
        report["comparison_sha256"] = digest(comparison_path)
        saved = json.loads(comparison_path.read_text())
        fresh = compare(root, calibration, cases)
        assert saved == fresh, "comparison differs from current source artifacts"
        assert fresh["calibration_sha256"] == criteria["calibration_sha256"]
        assert fresh["cases_sha256"] == criteria["cases_sha256"]
        by_id = {case["id"]: case for case in fresh["cases"]}
        assert len(by_id) == len(fresh["cases"])
        assert set(by_id) == {case["id"] for case in expected}
    except (AssertionError, KeyError, OSError, ValueError, TypeError) as error:
        reason = str(error) or type(error).__name__
        report["reasons"].append(f"input integrity or availability: {reason}")
        report["cases"] = [unknown_case(case["id"], reason) for case in expected]
        return report
    for case in expected:
        report["cases"].append(evaluate_case(
            case, by_id[case["id"]], criteria["role_limits"]))
    report["regression_status"] = combine(
        [case["regression_status"] for case in report["cases"]])
    report["decision_status"] = combine(
        [case["decision_status"] for case in report["cases"]])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_root", type=Path)
    parser.add_argument("criteria", type=Path)
    parser.add_argument("--comparison", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.private_root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / "build/private")
    comparison = args.comparison or root / "phase1b-calibrated-geometry.json"
    output = args.output or root / "phase1b-road-regression.json"
    assert output.resolve().is_relative_to(root)
    result = evaluate(root, args.criteria, comparison)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("regression", result["regression_status"], "decision",
          result["decision_status"])
    for case in result["cases"]:
        print(case["id"], case["regression_status"],
              case["decision_status"], case["role_status"])
    print("private result:", output)
    sys.exit({"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}[
        result["regression_status"]])
