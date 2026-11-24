# VERITAS AI — Documentation

These documents describe the **planned MVP** and the implemented P0 slice. They consolidate the original Word specifications and their enterprise update (v1.1). The original `.docx` files are retained for reference. What actually runs today is recorded in the root [README](../README.md) and `TODO.md`; everything else here remains planned.

1. [Product requirements](01_PRD.md) — scope, users, journeys and acceptance criteria.
2. [System architecture](02_System_Architecture.md) — service boundaries, execution and evidence.
3. [API contracts](03_API_Contracts.md) — proposed endpoint conventions and payloads; [openapi.json](openapi.json) is the generated snapshot of the running Harness.
4. [Implementation plan](04_Implementation_Plan.md) — milestones, tests and delivery.
5. [Security and threat model](05_Security_Threat_Model.md) — assets, threats and controls.
6. [TODO implementasi](TODO.md) — checklist prioritas, dependensi dan kriteria selesai untuk demo dan target lanjutan.
7. [Submission pack](submission.md) — draft deliverables, judge walkthrough, evidence map and claim guardrails (rules not yet confirmed).

## Katalog dan panduan

- [Katalog fitur](features.md), [istilah dan status](istilah.md), [batas AI](ai.md), serta [rencana CI/CD](ci-cd.md).
- [Threat model](threat-model/README.md): pihak, batas kepercayaan, ancaman, kontrol dan risiko terbuka.
- [Diagram arsitektur dan alur](architecture/README.md): setiap diagram memiliki sumber JSON dan HTML mandiri.

The specifications are a baseline for implementation, not a claim that the five-service target, Besu anchoring or the enterprise controls already exist. The approved focus is enterprise agent governance with **Control Before Action**, including a bounded outbound-data protection demonstration. The intended primary BUILD 2036 frontier is Applied AI & Agentic Intelligence; Digital Infrastructure is supporting context. The PRD and implementation plan distinguish the hackathon critical path from the broader platform target.
