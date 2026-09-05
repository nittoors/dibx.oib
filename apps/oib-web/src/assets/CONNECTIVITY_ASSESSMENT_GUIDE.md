# OIB Data Readiness & Connectivity Assessment Guide

Assess each asset/system on five dimensions:
1. **Connectivity** — Native Digital, Vendor Digital, Legacy Analog.
2. **Data rights** — whether Government-authorized systems can use/export operational data.
3. **Cyber path** — approved industrial/enterprise segment, review needed, isolated, or unknown.
4. **Historical depth** — data history available for model development and baselining.
5. **Data quality** — completeness, timestamps, units, identifiers, stability, and trustworthiness.

## Result bands
- **Green (75-100):** direct connector + pilot.
- **Yellow (45-74):** resolve access/cyber issues and/or use an adapter/gateway.
- **Red (<45):** sensor retrofit, OEM engagement, data-rights action, and a data-generation plan.

## Connectivity patterns to record
MTConnect, OPC UA, Modbus TCP, REST APIs, controller APIs, OEM cloud APIs, proprietary gateways, serial/PLC interfaces, retrofit sensors, and no interface.

## Procurement questions
- Does the Government have rights to export and reuse operational telemetry?
- Is API/interface documentation included?
- Are adapters or software licenses separately priced?
- Is third-party analytics integration permitted?
- Can data be consumed on-prem/edge without OEM cloud dependence?
- What cyber boundary and network segment will the asset use?
