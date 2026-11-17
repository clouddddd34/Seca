# Evidence and finding records

Use these labels consistently:

- **confirmed**: observed behavior or a complete deterministic code-path proof establishes the stated security control failure under explicit preconditions. A runtime exploitation claim requires runtime evidence.
- **likely**: substantial evidence supports the hypothesis, but a material precondition, control, or result remains unresolved.
- **unverified**: a pattern, scanner alert, or hypothesis requiring investigation. Do not present it as an established vulnerability.

Severity describes impact and conditions, not confidence. Use `unknown` until enough evidence exists. Do not invent numerical CVSS scores without calculating and recording their vector.

The log helper accepts one JSON object per finding file:

```json
{
  "id": "F-001",
  "title": "Example candidate awaiting verification",
  "status": "unverified",
  "severity": "unknown",
  "expected": "Describe the required control and its source.",
  "observed": "Describe exactly what was inspected or executed.",
  "evidence": [],
  "reproduction": [],
  "preconditions": [],
  "uncertainty": ["Runtime behavior has not been tested."],
  "impact": "Potential impact, clearly distinguished from demonstrated impact.",
  "remediation": "Proposed next step or correction."
}
```

For confirmed findings, provide nonempty `evidence` and `reproduction` lists. Evidence should point to redacted artifacts, test results, or precise code locations. Reproduction can describe deterministic code-path verification when live testing is unnecessary. Preserve the assessed revision/environment and relevant command in the evidence. Never use example records as actual findings.
