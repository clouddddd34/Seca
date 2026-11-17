use crate::Result;
use serde_json::{json, Value};
use std::{
    collections::HashSet,
    time::{SystemTime, UNIX_EPOCH},
};

pub fn new_log(target: &str, scope: &str) -> Value {
    json!({"schema_version": 1, "target": target, "scope": scope,
        "created_at": format!("unix:{}", SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs()),
        "coverage": [], "outstanding": [], "findings": []})
}

pub fn validate_finding(value: &Value) -> Result<()> {
    for field in [
        "id",
        "title",
        "expected",
        "observed",
        "impact",
        "remediation",
    ] {
        if value[field].as_str().is_none_or(|s| s.trim().is_empty()) {
            return Err(format!("Finding requires nonempty {field}"));
        }
    }
    if !matches!(
        value["status"].as_str(),
        Some("confirmed" | "likely" | "unverified")
    ) {
        return Err("Unknown finding status".into());
    }
    if !matches!(
        value["severity"].as_str(),
        Some("critical" | "high" | "medium" | "low" | "info" | "unknown")
    ) {
        return Err("Unknown severity".into());
    }
    for field in ["evidence", "reproduction", "preconditions", "uncertainty"] {
        let entries = value[field]
            .as_array()
            .ok_or(format!("{field} must be an array"))?;
        if entries
            .iter()
            .any(|v| v.as_str().is_none_or(|s| s.trim().is_empty()))
        {
            return Err(format!("{field} entries must be nonempty strings"));
        }
    }
    if value["status"] == "confirmed" {
        if value["evidence"].as_array().unwrap().is_empty()
            || value["reproduction"].as_array().unwrap().is_empty()
        {
            return Err("Confirmed findings require evidence and reproduction".into());
        }
    } else if value["uncertainty"].as_array().unwrap().is_empty() {
        return Err("Unconfirmed findings require remaining uncertainty".into());
    }
    Ok(())
}

pub fn validate_log(log: &Value) -> Result<()> {
    if log["schema_version"] != 1 {
        return Err("Unsupported ledger version".into());
    }
    for field in ["target", "scope", "created_at"] {
        if log[field].as_str().is_none_or(|s| s.trim().is_empty()) {
            return Err(format!("Log requires nonempty {field}"));
        }
    }
    for field in ["coverage", "outstanding", "findings"] {
        if !log[field].is_array() {
            return Err(format!("{field} must be an array"));
        }
    }
    let mut ids = HashSet::new();
    for finding in log["findings"].as_array().unwrap() {
        validate_finding(finding)?;
        if !ids.insert(finding["id"].as_str().unwrap()) {
            return Err("Duplicate finding ID".into());
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn finding() -> Value {
        json!({"id":"F-1","title":"Fixture","status":"confirmed","severity":"low",
            "expected":"Denied","observed":"Allowed","evidence":["Local test"],
            "reproduction":["Run test"],"preconditions":[],"uncertainty":[],
            "impact":"Fixture impact","remediation":"Enforce rule"})
    }
    #[test]
    fn rejects_unproven_confirmed_findings() {
        let mut value = finding();
        assert!(validate_finding(&value).is_ok());
        value["evidence"] = json!([]);
        assert!(validate_finding(&value).is_err());
        value["status"] = json!("unverified");
        assert!(validate_finding(&value).is_err());
        value["uncertainty"] = json!(["Not executed"]);
        assert!(validate_finding(&value).is_ok());
    }
    #[test]
    fn rejects_duplicate_ids() {
        let mut log = new_log("fixture", "local");
        log["findings"] = json!([finding(), finding()]);
        assert!(validate_log(&log).is_err());
    }
}
