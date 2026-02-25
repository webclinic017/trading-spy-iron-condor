# Prompt: Audit & Governance (/audit-governance)
Goal: Perform a semantic and structural audit of a specific module to ensure compliance with the North Star Directive.

## Parameters
- **Target Path:** {{path}} (Directory or file to audit)

## Audit Checklist
Please analyze the target code against these **AI-Driven Architecture** principles:

### 1. Transparency & Traceability
- Is every trading decision logged to the telemetry system?
- Does the code explain **WHY** a trade was taken, not just **WHAT**?

### 2. Risk Integrity (Rule #1)
- Are there any order submission calls that bypass `mandatory_trade_gate.py`?
- Is there a mandatory stop-loss attached to every opening order?

### 3. Logic "Phantom" Check
- Verify if any reported technical debt in comments actually exists in the code.
- Check for "hallucination loops" where code references non-existent dependencies.

### 4. Modular Compliance
- Does this feature follow the "Folder-as-Namespace" pattern?
- Are there cross-strategy dependencies that should be abstracted into `src/core`?

## Output Requirement
Return a **Governance Report** with:
- [ ] Compliance Score (0-100)
- [ ] List of "Shadow Risks" (Bypasses or unlogged logic)
- [ ] Required fixes to meet ADLC standards.
