# Data Provenance

## Public sources used to shape the synthetic model

### U.S. Army Organic Industrial Base modernization
Army public materials describe a 23-site OIB and a 15-year modernization effort exceeding $18B, with emphasis on facilities, processes, workforce, digital infrastructure, and data-driven industrial operations.
Source: https://www.army.mil/article/292392/supporting_the_digital_foundation_for_the_armys_organic_industrial_base_transformation

### NASA Prognostics Center of Excellence / C-MAPSS
NASA's public prognostics repository includes time-series datasets from nominal to failed states and C-MAPSS turbofan degradation simulations with multiple operating conditions, fault modes, and sensor channels. The prototype uses these concepts to shape condition-monitoring and predictive-maintenance logic; no NASA values are relabeled as Army/OEM values.
Source: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/

### DLA PUB LOG
DLA PUB LOG provides publicly releasable Federal Logistics Information System information, including unrestricted NSN data, Federal Supply Classification, and CAGE-related catalog information. The prototype uses FSC/CAGE-like structures only; all part IDs, quantities, supplier relationships, lead times, and supply risks are synthetic.
Source: https://www.dla.mil/Information-Operations/Services/Applications/PUB-LOG/

### O*NET
O*NET provides occupations, skills, tasks, work activities, work context, and downloadable data formats. The prototype uses O*NET-style occupational/skill structure. All worker IDs, availability, training status, certifications, and capacity values are synthetic.
Source: https://www.onetcenter.org/database.html

## Synthetic/invented fields
All asset identities, manufacturers labeled with `-like`, operating health, failure probability, work orders, worker records, parts demand, inventory, production constraints, quality findings, readiness scores, and AI recommendations are simulation artifacts.

## Intended demo claim
This prototype demonstrates data relationships, ingestion architecture, operational reasoning, and user experience. It does not claim validated prediction accuracy against Army or OEM data.
