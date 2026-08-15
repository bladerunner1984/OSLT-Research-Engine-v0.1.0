# OSLT v2.1 Security, Prompt-Isolation and Blinding Specification

Retrieved webpages, documents, social-media posts, model/tool outputs and external archives are untrusted evidence data. OSLT preserves the original content but wraps analysis copies inside an explicit untrusted-data boundary.

Instruction-like strings are detection signals, not executable commands. Regex/pattern detection is only one defence and must not be represented as complete prompt-injection prevention.

Tools are allow-listed per analyst role and irreversible actions are disabled by default. Cross-domain analytical conclusions can be sealed until prespecified analysis completion. All tool/model actions should be attributable to the originating run and evidence context.
