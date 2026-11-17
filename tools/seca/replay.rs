use crate::Result;
use reqwest::{
    blocking::Client,
    header::{HeaderValue, AUTHORIZATION},
    redirect::Policy,
    Url,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::{
    collections::HashSet,
    io::Read,
    net::IpAddr,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    scope_origin: String,
    url: String,
    safe_to_read: bool,
    accounts: Vec<Account>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Account {
    label: String,
    token_env: Option<String>,
    expected_status: u16,
    expect_json: Option<Expectation>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Expectation {
    pointer: String,
    value: Value,
}

fn validate_url(config: &Config, remote: bool) -> Result<Url> {
    let scope = Url::parse(&config.scope_origin).map_err(|_| "Invalid scope origin")?;
    let url = Url::parse(&config.url).map_err(|_| "Invalid target URL")?;
    for item in [&scope, &url] {
        if !matches!(item.scheme(), "http" | "https")
            || item.host_str().is_none()
            || !item.username().is_empty()
            || item.password().is_some()
            || item.fragment().is_some()
        {
            return Err("URLs must be HTTP(S) without user information or fragments".into());
        }
    }
    if scope.path() != "/" || scope.query().is_some() || scope.origin() != url.origin() {
        return Err("Target must match the exact configured scheme, host and port".into());
    }
    // Only literal loopback IPs qualify. DNS names cannot bypass the remote gate.
    let local = url
        .host_str()
        .unwrap()
        .trim_matches(['[', ']'])
        .parse::<IpAddr>()
        .is_ok_and(|ip| ip.is_loopback());
    if !local && (!remote || url.scheme() != "https") {
        return Err("Non-loopback targets require HTTPS and --allow-remote".into());
    }
    if !config.safe_to_read {
        return Err(
            "Confirm this endpoint has no state-changing behavior with safe_to_read".into(),
        );
    }
    Ok(url)
}

pub fn execute(value: Value, remote: bool) -> Result<Value> {
    let config: Config =
        serde_json::from_value(value).map_err(|_| "Invalid replay configuration")?;
    let url = validate_url(&config, remote)?;
    if !(1..=8).contains(&config.accounts.len()) {
        return Err("Use 1 to 8 accounts".into());
    }
    let mut labels = HashSet::new();
    let mut tokens = Vec::new();
    // Validate all inputs and credentials before the first request.
    for account in &config.accounts {
        if account.label.is_empty()
            || account.label.len() > 64
            || !account
                .label
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || "_-".contains(c))
            || !labels.insert(&account.label)
            || !(100..=599).contains(&account.expected_status)
        {
            return Err(
                "Account labels must be unique simple identifiers; status must be 100–599".into(),
            );
        }
        if let Some(expected) = &account.expect_json {
            if !expected.pointer.is_empty() && !expected.pointer.starts_with('/') {
                return Err("Expected JSON pointer must be empty or begin with /".into());
            }
        }
        tokens.push(match &account.token_env {
            Some(name) => {
                let token = std::env::var(name)
                    .map_err(|_| "A configured token environment variable is missing")?;
                if token.trim().is_empty() {
                    return Err("A configured token is empty".into());
                }
                let mut header = HeaderValue::from_str(&format!("Bearer {token}"))
                    .map_err(|_| "Invalid bearer token header")?;
                header.set_sensitive(true);
                Some(header)
            }
            None => None,
        });
    }
    let client = Client::builder()
        .redirect(Policy::none())
        .no_proxy()
        .retry(reqwest::retry::never())
        .timeout(Duration::from_secs(10))
        .connect_timeout(Duration::from_secs(3))
        .user_agent("Seca/0.1 authorized-review")
        .build()
        .map_err(|_| "Cannot initialize HTTP client")?;
    let mut observations = Vec::new();
    for (account, token) in config.accounts.iter().zip(tokens) {
        let mut request = client.get(url.clone());
        if let Some(token) = token {
            request = request.header(AUTHORIZATION, token);
        }
        let mut observation =
            json!({"account": account.label, "expected_status": account.expected_status});
        match request.send() {
            Err(_) => observation["error"] = json!("Request failed (transport, TLS, or timeout); details withheld to avoid credential leakage"),
            Ok(response) => {
                let status = response.status().as_u16();
                observation["status"] = json!(status);
                observation["status_matches"] = json!(status == account.expected_status);
                let mut bytes = Vec::new();
                match response.take(65537).read_to_end(&mut bytes) {
                    Err(_) => observation["error"] = json!("Response read failed"),
                    Ok(_) => {
                        let truncated = bytes.len() > 65536;
                        observation["body_truncated"] = json!(truncated);
                        observation["bytes_read"] = json!(bytes.len());
                        if let Some(expected) = &account.expect_json {
                            let body = if truncated { None } else { serde_json::from_slice::<Value>(&bytes).ok() };
                            observation["json_check_evaluated"] = json!(body.is_some());
                            observation["json_matches"] = match body {
                                Some(body) => json!(body.pointer(&expected.pointer) == Some(&expected.value)),
                                None => Value::Null,
                            };
                        }
                    }
                }
            }
        }
        let failed = observation.get("error").is_some();
        observations.push(observation);
        if failed {
            break;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    Ok(
        json!({"schema_version": 1, "tool": "seca", "version": env!("CARGO_PKG_VERSION"),
        "observed_at_unix": SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs(),
        "method": "GET", "accounts_planned": config.accounts.len(), "accounts_attempted": observations.len(),
        "note": "Observations only, not vulnerability verdicts. URL, credentials, headers, and response bodies are deliberately omitted. Keep a redacted reproduction separately.",
        "observations": observations}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn config(url: &str, scope: &str) -> Config {
        Config {
            url: url.into(),
            scope_origin: scope.into(),
            safe_to_read: true,
            accounts: vec![],
        }
    }
    #[test]
    fn gates_scope_and_remote_transport() {
        assert!(validate_url(
            &config("http://127.0.0.1:8765/me", "http://127.0.0.1:8765"),
            false
        )
        .is_ok());
        assert!(validate_url(
            &config("http://127.0.0.1:8766/me", "http://127.0.0.1:8765"),
            false
        )
        .is_err());
        assert!(validate_url(
            &config("http://example.test/me", "http://example.test"),
            true
        )
        .is_err());
        assert!(validate_url(
            &config("https://example.test/me", "https://example.test"),
            false
        )
        .is_err());
        assert!(validate_url(
            &config("https://example.test/me", "https://example.test"),
            true
        )
        .is_ok());
        assert!(validate_url(
            &config("http://token@127.0.0.1/me", "http://127.0.0.1"),
            false
        )
        .is_err());
        assert!(validate_url(&config("file:///tmp/file", "file:///"), false).is_err());
    }
}
