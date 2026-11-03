# Data Privacy and the GDPR: Principles, Health Data, Minimisation and External AI Services

The General Data Protection Regulation (GDPR) is the European Union's main data protection law. It has applied since May 2018 and governs how organisations collect, use, store and share personal data about people in the EU. Its reach goes beyond the EU: organisations established elsewhere can be covered if they offer goods or services to people in the EU or monitor their behaviour. The United Kingdom keeps a closely related regime, often called the UK GDPR, alongside its own data protection legislation. This article outlines the GDPR's core principles, the special rules for sensitive data such as health information, the principle of data minimisation, and the particular risks that arise when personal data is sent to external APIs and large language model (LLM) providers.

This article is general information, not legal advice; organisations should seek qualified legal counsel for specific compliance questions.

## Key Concepts

- **Personal data:** any information relating to an identified or identifiable natural person. This includes obvious identifiers such as names and email addresses, and also online identifiers, location data and combinations of attributes that could identify someone.
- **Processing:** almost any operation performed on personal data, including collection, storage, analysis, disclosure and deletion.
- **Controller:** the organisation that decides the purposes and means of processing.
- **Processor:** an organisation that processes personal data on behalf of a controller, such as a cloud provider or software-as-a-service vendor.
- **Pseudonymisation versus anonymisation:** pseudonymised data, where identifiers are replaced but re-identification is possible with additional information, is still personal data. Truly anonymised data falls outside the GDPR, but genuine anonymisation is hard to achieve.

## The Core Principles

Article 5 of the GDPR sets out principles that apply to all processing:

1. **Lawfulness, fairness and transparency.** Processing must have a legal basis and be clearly explained to the people concerned.
2. **Purpose limitation.** Data must be collected for specified, explicit and legitimate purposes and not further processed in ways incompatible with those purposes.
3. **Data minimisation.** Data must be adequate, relevant and limited to what is necessary.
4. **Accuracy.** Data must be accurate and kept up to date.
5. **Storage limitation.** Data must not be kept in identifiable form for longer than necessary.
6. **Integrity and confidentiality.** Appropriate security must protect data against unauthorised access, loss or damage.
7. **Accountability.** The controller is responsible for compliance and must be able to demonstrate it.

Processing also needs one of six **lawful bases**: consent, contract, legal obligation, vital interests, public task, or legitimate interests. Each comes with its own conditions. Consent, for instance, must be freely given, specific, informed and unambiguous, and as easy to withdraw as to give.

Individuals have rights including access, rectification, erasure, restriction, data portability, objection, and rights relating to automated decision-making that has legal or similarly significant effects.

## Special Category Data, Including Health

Article 9 defines **special categories** of personal data that need extra protection. These are data revealing racial or ethnic origin, political opinions, religious or philosophical beliefs and trade union membership, plus genetic data, biometric data used for identification, data concerning health, and data concerning a person's sex life or sexual orientation.

Processing special category data is prohibited unless one of a limited set of conditions applies, in addition to a lawful basis. Conditions include explicit consent, employment and social security obligations, vital interests, health or social care purposes under professional confidentiality, public health, and scientific research with appropriate safeguards. Member states may add further conditions or limitations.

**Health data** is interpreted broadly. It can include medical diagnoses, test results such as blood glucose readings, prescriptions and fitness tracker data, and also information from which health status can be inferred. Personal notes about symptoms, diets or sleep patterns held by an app may count as health data. Processing it at scale, or using new technologies, often requires a **data protection impact assessment (DPIA)**.

## Data Minimisation in Practice

Data minimisation asks whether each data element is truly necessary for the stated purpose. Practical techniques include:

- collecting only fields that are needed, and making optional fields genuinely optional;
- aggregating or summarising data rather than storing raw records;
- pseudonymising or tokenising identifiers before analysis;
- redacting names, contact details and other identifiers from free text;
- setting retention periods and deleting data automatically when they expire;
- limiting access through role-based permissions;
- applying "data protection by design and by default" (Article 25), so that the most privacy-protective settings are the default.

Minimisation also reduces the damage when security incidents occur, since data that was never collected cannot be breached.

## Risks of Sending Personal Data to External APIs and LLM Providers

Many applications now send user content to third-party services, such as translation, analytics, search and generative AI models accessed via API. When that content includes personal data, the GDPR applies to the transfer and to what the provider does with the data. Key risks and considerations include:

- **Role and contracts.** The provider is typically a processor and needs a **data processing agreement** under Article 28 that limits processing to the controller's instructions. If the provider uses the data for its own purposes, such as model training, it may be acting as a controller, which needs separate justification and transparency.
- **International transfers.** Sending data outside the European Economic Area requires a valid transfer mechanism, such as an adequacy decision, standard contractual clauses with a transfer impact assessment, or another approved safeguard. Legal frameworks for EU–US transfers have been challenged and replaced more than once, so organisations need to keep track of current arrangements.
- **Training and retention.** Some services may retain prompts and outputs for abuse monitoring, debugging or model improvement. Retention periods and opt-out options vary by provider and plan, and data that becomes part of training sets may be hard to remove.
- **Purpose limitation and transparency.** Users may not expect their notes, messages or health information to be shared with an AI provider. Privacy notices need to disclose such sharing.
- **Special category data.** Sending health or other sensitive data to an external model needs an Article 9 condition. In many consumer contexts explicit consent will be the relevant condition, and a DPIA is often advisable.
- **Inference and output risks.** Models may infer sensitive attributes from seemingly harmless input, produce inaccurate statements about individuals, or reproduce personal data in outputs. Accuracy and erasure rights can be hard to honour for model outputs.
- **Security.** API keys, logs and intermediate caches can expose data. Prompt injection and data exfiltration attacks are emerging concerns.

Common mitigations include redacting or pseudonymising data before sending it, routing only the minimum context needed for a task, preferring providers with zero-retention or no-training options, keeping processing local or within the EEA where feasible, logging what is sent, and giving users clear choices. Regulators in several countries have issued guidance on AI and data protection. The EU's AI Act adds a separate layer of obligations alongside the GDPR rather than replacing it.

## Enforcement

National supervisory authorities enforce the GDPR. Fines can reach up to 20 million euros or 4 percent of worldwide annual turnover, whichever is higher, for the most serious infringements. Authorities can also order processing to stop. Individuals can bring complaints and, in some cases, claim compensation. Enforcement practice differs between countries, and the interpretation of several provisions continues to develop through court decisions and regulatory guidance.

## Summary

The GDPR is built on principles of lawfulness, purpose limitation, data minimisation, accuracy, storage limitation, security and accountability. Health data is special category data that needs both a lawful basis and an Article 9 condition. Data minimisation is a core safeguard that also reduces security risk. Sending personal data, and especially sensitive data, to external APIs and LLM providers raises issues of processor contracts, international transfers, retention, training use and transparency. Redaction, minimal context and careful provider selection can reduce these risks.
