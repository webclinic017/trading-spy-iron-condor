#!/usr/bin/env ts-node
/**
 * MemAlign - Lightweight dual-memory store for RLHF signals.
 *
 * Stores:
 * - episodes.jsonl: every feedback event with context
 * - principles.jsonl: distilled principles for fast retrieval
 */

import { appendFileSync, existsSync, mkdirSync, readFileSync } from "fs";
import { join } from "path";

export interface Feedback {
  taskId: string;
  agentDecision: string;
  userFeedback: string;
  sentiment: "positive" | "negative";
  timestamp: string;
  intensity?: number;
  toolName?: string;
  files?: string[];
}

export interface MemAlignResult {
  principle: string;
  episodeId: string;
}

export class MemAlign {
  private baseDir: string;
  private episodesPath: string;
  private principlesPath: string;

  constructor() {
    this.baseDir = join(process.cwd(), ".claude", "memory", "memalign");
    this.episodesPath = join(this.baseDir, "episodes.jsonl");
    this.principlesPath = join(this.baseDir, "principles.jsonl");
  }

  private ensureDirs(): void {
    mkdirSync(this.baseDir, { recursive: true });
  }

  private derivePrinciple(feedback: Feedback): string {
    const decision = (feedback.agentDecision || "").trim() || "unknown decision";
    if (feedback.sentiment === "negative") {
      return `Avoid: ${decision}`;
    }
    return `Prefer: ${decision}`;
  }

  async learn(feedback: Feedback): Promise<MemAlignResult> {
    this.ensureDirs();
    const episodeId = `ep_${Date.now()}_${Math.floor(Math.random() * 1e6)}`;
    const principle = this.derivePrinciple(feedback);

    const episode = {
      id: episodeId,
      ...feedback,
      principle,
    };

    const principleRecord = {
      id: episodeId,
      principle,
      sentiment: feedback.sentiment,
      timestamp: feedback.timestamp,
      intensity: feedback.intensity,
      toolName: feedback.toolName,
      files: feedback.files,
    };

    appendFileSync(this.episodesPath, JSON.stringify(episode) + "\n");
    appendFileSync(this.principlesPath, JSON.stringify(principleRecord) + "\n");

    return { principle, episodeId };
  }

  searchPrinciples(query: string, limit = 5): string[] {
    if (!existsSync(this.principlesPath)) return [];
    const q = query.toLowerCase();
    const lines = readFileSync(this.principlesPath, "utf-8")
      .split("\n")
      .filter(Boolean);

    const matches: string[] = [];
    for (const line of lines) {
      try {
        const item = JSON.parse(line);
        const text = String(item.principle || "").toLowerCase();
        if (text.includes(q)) {
          matches.push(item.principle);
          if (matches.length >= limit) break;
        }
      } catch {
        // skip
      }
    }
    return matches;
  }
}
