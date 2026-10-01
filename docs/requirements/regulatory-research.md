# Regulatory research - grounding the risk decomposition

The brief says the decomposition must be "grounded in published supervisory
frameworks, not invented". This note records which frameworks we used, what we
took from each, and where it shows up in the product. Produced by the
requirements-analyst agent from public sources, then reviewed by a human
(review notes at the bottom). Paragraph-level references should be re-verified
against the current published text before any real-world use.

## 1. Why a pre-launch assessment is required at all

| Source | What it says (summary) | Used for |
|---|---|---|
| **FATF Recommendation 15 - New technologies** ([FATF Recommendations](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html)) | Countries and financial institutions should identify and assess ML/TF risks arising from new products, new business practices, new delivery mechanisms and new or developing technologies, and the assessment should take place **prior to launch**. | The six change types we accept at intake; the hard rule that nothing goes live before a committee decision. |
| **OCC Bulletin 2017-43, New, Modified, or Expanded Bank Products and Services: Risk Management Principles** ([OCC](https://www.occ.gov/news-issuances/bulletins/2017/bulletin-2017-43.html)) | Banks should have effective risk management for new, modified or expanded products, including due diligence, approval by appropriate management, and performance monitoring after launch. | "Modified / expanded" are first-class change types; post-approval conditions and monitoring are captured on the decision. |
| **FFIEC BSA/AML Examination Manual - BSA/AML Risk Assessment** ([FFIEC](https://bsaaml.ffiec.gov/manual/BSAAMLRiskAssessment/01)) | A bank's risk assessment should identify specific risk categories (products, services, customers, entities, transactions and geographic locations) and be updated when new products, services or customer types are introduced. | Our inherent-risk dimensions. Examiners use this manual, so mapping to it makes our output examiner-readable. |

## 2. How risk is decomposed (inherent -> controls -> residual)

| Source | What it says (summary) | Used for |
|---|---|---|
| **Wolfsberg Group - FAQs on Risk Assessments for Money Laundering, Sanctions and Bribery & Corruption** ([Wolfsberg Group](https://www.wolfsberg-group.org/)) | Describes the industry methodology: assess **inherent risk**, evaluate **control effectiveness** (design and operation), derive **residual risk**; keep the methodology documented and consistent. | The inherent / control / residual scoring model, and separating design effectiveness from operating effectiveness. |
| **FATF Guidance for a Risk-Based Approach: The Banking Sector** ([FATF, 2014](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Risk-based-approach-banking-sector.html)) | Risk factors fall into country/geographic, customer, and product/service/transaction/delivery-channel risk. Mitigation is proportionate to risk; a risk-based approach does not mean zero risk. | Dimension definitions; the principle that controls reduce but never eliminate residual risk. |
| **Basel Committee - Sound management of risks related to money laundering and financing of terrorism** ([BIS](https://www.bis.org/bcbs/publ/d505.htm)) | Banks should identify, assess and understand ML/FT risks across customers, products, channels and geographies, with governance by the board and senior management. | Committee governance (G3), and "risk appetite" thresholds in config. |
| **OFAC - A Framework for OFAC Compliance Commitments (2019)** ([US Treasury](https://ofac.treasury.gov/)) | Five components: management commitment, **risk assessment**, internal controls, testing/auditing, training. Risk assessment covers customers, products, services, supply chain, intermediaries, counter-parties, transactions and geographies. | Sanctions as a separate risk type; third-party/vendor as a dimension. |
| **FinCEN Customer Due Diligence Rule, 31 CFR 1010.230** ([eCFR](https://www.ecfr.gov/current/title-31/subtitle-B/chapter-X/part-1010/subpart-B/section-1010.230)) | Identify and verify beneficial owners of legal-entity customers; understand the nature and purpose of customer relationships. | Customer-dimension rules (legal entities, opaque ownership). |
| **Interagency Guidance on Third-Party Relationships: Risk Management (2023)** ([Federal Reserve / FDIC / OCC](https://www.federalreserve.gov/supervisionreg/srletters/SR2310.htm)) | Risk management for third-party relationships across their life cycle, proportionate to risk and criticality. | The Third Parties / Vendors dimension and "vendor onboarding" change type. |
| **FATF high-risk and other monitored jurisdictions lists** ([FATF](https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html)) | Public "call for action" and "increased monitoring" lists. | Deterministic geography rules. Our synthetic list is modelled on the *structure* of these lists; countries are fictional. |

## 3. Governing the AI itself

| Source | Used for |
|---|---|
| **Federal Reserve SR 11-7 / OCC 2011-12, Supervisory Guidance on Model Risk Management** ([Federal Reserve](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)) | The scoring engine and LLM components are treated as "models": documented, validated (our eval suite), with effective challenge (human gates) and ongoing monitoring (ops dashboards, override-rate drift alerts). |
| **NIST AI Risk Management Framework 1.0** ([NIST](https://www.nist.gov/itl/ai-risk-management-framework)) | Govern / Map / Measure / Manage structure for `docs/governance/ai-governance.md`. |

## 4. Resulting decomposition

Risk **types** (what can go wrong): Money Laundering (AML), Terrorist Financing
(TF), Sanctions, Fraud, Bribery and Corruption (ABC).

Inherent risk **dimensions** (where it comes from), from FFIEC + FATF + OFAC:

| Code | Dimension | Example drivers |
|---|---|---|
| PRD | Products and Services | anonymity, cash intensity, cross-border value transfer, crypto/virtual assets, speed of funds movement |
| CUS | Customers and Entities | legal entities, PEPs, MSBs, non-resident, opaque ownership, new segment |
| GEO | Geography | high-risk / monitored jurisdictions, sanctioned regions, new markets |
| CHN | Delivery Channels | non-face-to-face onboarding, API/embedded finance, agents and intermediaries |
| TRX | Transactions | volume, value, velocity, third-party payments, instant settlement |
| TPV | Third Parties and Vendors | outsourcing of KYC/monitoring, offshore processors, sub-contractors |

Each dimension is scored on likelihood x impact (1-5 each), then mitigated by
mapped controls. See `docs/architecture/adr/ADR-001-deterministic-scoring.md`.

## Review decisions (requirements stage - human lead to confirm or amend)
- Removed an agent-proposed seventh dimension ("Reputational risk"): it is an
  *impact* of financial crime, not a source of it. Kept as part of the impact scale.
- Replaced specific paragraph numbers the agent offered for the Wolfsberg FAQ
  with the document title only; the paragraph numbers could not be verified.
- Real country names are not used in the jurisdiction list (synthetic-data rule);
  fictional jurisdictions are tagged with the list category they model.
