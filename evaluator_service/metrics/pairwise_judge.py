"""
Pairwise LLM judge for comparing two document sequences.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

from evaluator_service.adapters.azure_openai import chat_json
from evaluator_service.utils.pdf_extractor import extract_text_from_pdf


class PairwiseJudge:
    """Run pairwise comparisons with random order shuffling."""

    _DEFAULT_REASONING = "Judge response could not be parsed reliably."

    def _normalize_documents(self, documents: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in documents:
            candidate = (item or "").strip()
            if not candidate:
                normalized.append("")
                continue

            path = Path(candidate)
            if path.exists() and path.is_file() and path.suffix.lower() == ".pdf":
                text = extract_text_from_pdf(str(path))
                normalized.append((text or "").strip())
            else:
                normalized.append(candidate)
        return normalized

    @staticmethod
    def _format_sequence(documents: list[str]) -> str:
        parts: list[str] = []
        for idx, doc in enumerate(documents, start=1):
            parts.append(f"--- Document {idx} ---\n{(doc or '').strip()}")
        return "\n\n".join(parts).strip()

    @staticmethod
    def _criteria_definitions() -> dict[str, str]:
        return {
            "coherence": "Each document flows naturally from the previous one",
            "dependency_flow": "Concepts introduced early are properly built upon later",
            "content_progression": "The sequence moves from foundational to advanced topics logically",
            "non_redundancy": "Information is not repeated unnecessarily across documents",
        }

    def _build_prompt(
        self, *, sequence_x: list[str], sequence_y: list[str], criteria: list[str]
    ) -> str:
        definitions = self._criteria_definitions()
        rendered_criteria = []
        for c in criteria:
            rendered_criteria.append(
                f"- {c}: {definitions.get(c, 'Evaluate this criterion carefully')}")

        criteria_text = "\n".join(rendered_criteria)
        sequence_x_content = self._format_sequence(sequence_x)
        sequence_y_content = self._format_sequence(sequence_y)

        return f"""You are an expert evaluator of AI-generated document sequences.

You will be given two sequences of documents (Sequence X and Sequence Y).
Each sequence was generated to cover a series of related topics in order.

Evaluate which sequence is better based on the following criteria:
{criteria_text}

Definitions:
- Coherence: Each document flows naturally from the previous one
- Dependency flow: Concepts introduced early are properly built upon later
- Content progression: The sequence moves from foundational to advanced topics logically
- Non-redundancy: Information is not repeated unnecessarily across documents

--- Sequence X ---
{sequence_x_content}

--- Sequence Y ---
{sequence_y_content}

Based on your evaluation, respond in this exact JSON format:
{{
  "winner": "X" or "Y" or "tie",
  "reasoning": "Your detailed explanation here",
  "criteria_scores": {{
    "coherence": {{"X": 1-5, "Y": 1-5}},
    "dependency_flow": {{"X": 1-5, "Y": 1-5}},
    "content_progression": {{"X": 1-5, "Y": 1-5}},
    "non_redundancy": {{"X": 1-5, "Y": 1-5}}
  }}
}}

Do not reveal any preference based on order. Judge purely on quality.
"""

    @staticmethod
    def _parse_winner(data: dict[str, Any]) -> str | None:
        winner = data.get("winner")
        if not isinstance(winner, str):
            return None
        w = winner.strip().lower()
        if w in {"x", "y", "tie"}:
            return w
        return None

    def run_single_comparison(
        self,
        doc_a: list[str],
        doc_b: list[str],
        label_a: str,
        label_b: str,
        criteria: list[str],
    ) -> dict[str, Any]:
        prompt = self._build_prompt(
            sequence_x=doc_a, sequence_y=doc_b, criteria=criteria)

        attempts = 0
        max_attempts = 3
        last_reasoning = self._DEFAULT_REASONING

        while attempts < max_attempts:
            attempts += 1
            print(
                f"  [run_single_comparison] Attempt {attempts}/{max_attempts} — X={label_a}, Y={label_b}")

            try:
                data = chat_json(
                    system="You are a strict JSON evaluator. Output JSON only.",
                    user=prompt,
                    model="gpt-4o",
                    temperature=0,
                    max_output_tokens=1200,
                )

            except Exception as e:
                print(
                    f"  [run_single_comparison] Attempt {attempts} — EXCEPTION: {type(e).__name__}: {e}")
                if attempts < max_attempts:
                    sleep_time = 10 * attempts
                    print(
                        f"  [run_single_comparison] Sleeping {sleep_time}s before retry...")
                    time.sleep(sleep_time)
                continue

            reasoning = data.get("reasoning")
            if isinstance(reasoning, str) and reasoning.strip():
                last_reasoning = reasoning.strip()
            else:
                print(
                    f"  [run_single_comparison] Attempt {attempts} — reasoning missing or invalid: {reasoning!r}")

            winner = self._parse_winner(data)
            if winner is None:
                print(
                    f"  [run_single_comparison] Attempt {attempts} — winner parsing FAILED. winner field was: {data.get('winner')!r}")
                if attempts < max_attempts:
                    print(
                        f"  [run_single_comparison] Sleeping 20s before retry...")
                    time.sleep(20)
                continue

            print(f"  [run_single_comparison] Attempt {attempts} — SUCCESS.")

            if winner == "x":
                mapped_winner = label_a
            elif winner == "y":
                mapped_winner = label_b
            else:
                mapped_winner = "tie"

            return {
                "winner": mapped_winner,
                "winner_xy": winner.upper() if winner in {"x", "y"} else "tie",
                "reasoning": last_reasoning,
                "criteria_scores": data.get("criteria_scores", {}),
            }

        print(
            f"  [run_single_comparison] All {max_attempts} attempts failed. Returning tie as fallback.")
        return {
            "winner": "tie",
            "winner_xy": "tie",
            "reasoning": last_reasoning,
            "criteria_scores": {},
        }

    def run_evaluation(
        self,
        sequence_a: dict[str, Any],
        sequence_b: dict[str, Any],
        criteria: list[str],
        runs: int,
    ) -> dict[str, Any]:
        docs_a = self._normalize_documents(sequence_a.get("documents", []))
        docs_b = self._normalize_documents(sequence_b.get("documents", []))

        if not docs_a or not docs_b:
            raise ValueError(
                "Both sequences must include at least one document.")

        win_counts = {"sequence_a": 0, "sequence_b": 0, "tie": 0}
        run_details: list[dict[str, Any]] = []

        for run_idx in range(1, runs + 1):
            print(f"\n[run_evaluation] Starting run {run_idx}/{runs}...")

            order = [
                ("sequence_a", docs_a),
                ("sequence_b", docs_b),
            ]
            random.shuffle(order)

            x_label, x_docs = order[0]
            y_label, y_docs = order[1]

            print(
                f"[run_evaluation] Run {run_idx} — order shown: X={x_label}, Y={y_label}")

            result = self.run_single_comparison(
                doc_a=x_docs,
                doc_b=y_docs,
                label_a=x_label,
                label_b=y_label,
                criteria=criteria,
            )

            winner = result["winner"]
            win_counts[winner] += 1
            print(
                f"[run_evaluation] Run {run_idx} — winner: {winner}, counts so far: {win_counts}")

            run_details.append(
                {
                    "run": run_idx,
                    "order_shown": [x_label, y_label],
                    "winner": winner,
                    "reasoning": result.get("reasoning", self._DEFAULT_REASONING),
                    "criteria_scores": result.get("criteria_scores", {}),
                }
            )

            if run_idx < runs:
                print(f"[run_evaluation] Sleeping 20s before next run...")
                time.sleep(20)

        a_rate = round(win_counts["sequence_a"] / runs, 2) if runs else 0.0
        b_rate = round(win_counts["sequence_b"] / runs, 2) if runs else 0.0
        win_rate = {"sequence_a": a_rate, "sequence_b": b_rate}

        if win_counts["sequence_a"] > win_counts["sequence_b"]:
            overall_winner = "sequence_a"
        elif win_counts["sequence_b"] > win_counts["sequence_a"]:
            overall_winner = "sequence_b"
        else:
            overall_winner = "tie"

        if overall_winner == "tie":
            consensus = "tie across runs"
        else:
            pct = int(round(win_rate[overall_winner] * 100))
            consensus = f"{overall_winner} wins with {pct}% win rate"

        print(
            f"\n[run_evaluation] DONE. Winner: {overall_winner} | consensus: {consensus}")

        return {
            "winner": overall_winner,
            "win_counts": win_counts,
            "win_rate": win_rate,
            "run_details": run_details,
            "consensus": consensus,
        }
