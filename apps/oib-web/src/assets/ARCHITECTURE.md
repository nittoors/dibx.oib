# Architecture

Synthetic CSV/DB today -> replaceable ingestion adapters -> common depot data model -> module-specific AI -> command-level readiness reasoning.

Production connectors may include MTConnect, OPC UA, Modbus, OEM APIs, Army maintenance/ERP/logistics systems, workforce systems, quality systems, and retrofit edge gateways.

The prototype intentionally separates source systems from normalized objects so real data can replace synthetic data without redesigning the user experience.
