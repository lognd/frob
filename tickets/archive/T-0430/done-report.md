## Done report

Extend PII010 FIELD_SIGNATURES with 18 GDPR/CCPA/HIPAA/PCI-DSS/NIST-800-122 field-name entries (account/license/vehicle/device ids, medical-record/beneficiary numbers, maiden name, geolocation, GDPR Art.9(1) special categories). TestDriftLock parametrization auto-covers each. Reviewer APPROVED.

### Changed
```
 src/frob/gates/_pii_structural.py | 56 +++++++++++++++++++++++++++++++++++++++
 1 file changed, 56 insertions(+)
```

### Evidence
(no evidence recorded)
