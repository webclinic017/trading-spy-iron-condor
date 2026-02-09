#!/usr/bin/env ts-node
/**
 * CortexWriter - Human-readable audit trail for RLHF feedback.
 *
 * Writes:
 * - cortex_ledger.jsonl (structured)
 * - lessons-learned.memory.md (readable summary)
 */

import { appendFileSync, mkdirSync } from "fs";
import { join } from "path";

export interface CortexEntry {
  timestamp: string;
  taskId: string;
  principle: string;
  context: string;
  sentiment: "positive" | "negative";
  confidence: number;
  domain: string;
  toolName?: string;
  files?: string[];
}

export class CortexWriter {
  private baseDir: string;
  private ledgerPath: string;
  private markdownPath: string;

  constructor() {
    this.baseDir = join(process.cwd(), ".claude", "memory", "feedback");
    this.ledgerPath = join(this.baseDir, "cortex_ledger.jsonl");
    this.markdownPath = join(
      process.cwd(),
      ".claude",
      "memory",
      "lessons-learned.memory.md",
    );
  }

  private ensureDirs(): void {
    mkdirSync(this.baseDir, { recursive: true });
  }

  async appendFeedback(entry: CortexEntry): Promise<void> {
    this.ensureDirs();

    appendFileSync(this.ledgerPath, JSON.stringify(entry) + "\n");
    appendFileSync(this.markdownPath, this.formatMarkdown(entry));
  }

  private formatMarkdown(entry: CortexEntry): string {
    const lines: string[] = [];
    lines.push("\n---\n");
    lines.push(`### ${entry.timestamp} | ${entry.sentiment.toUpperCase()}`);
    lines.push("");
    lines.push(`- Task: ${entry.taskId}`);
    lines.push(`- Domain: ${entry.domain}`);
    lines.push(`- Confidence: ${entry.confidence.toFixed(2)}`);
    lines.push(`- Principle: ${entry.principle}`);
    if (entry.toolName) lines.push(`- Tool: ${entry.toolName}`);
    if (entry.files && entry.files.length) {
      lines.push(`- Files: ${entry.files.join(", ")}`);
    }
    if (entry.context) {
      lines.push("");
      lines.push("Context:");
      lines.push(entry.context);
    }
    lines.push("");
    return lines.join("\n");
  }
}
