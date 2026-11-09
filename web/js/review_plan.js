/* Mailroom review desk — what a resolve click sends. Vanilla, DOM-free.
 *
 * Shared by the pixel console (web/js/api.js) and the hosted Observatory
 * (hosted/js/app.js) so both desks build the same request. Pure functions
 * only: no DOM, no fetch, so the module also runs in `node` (tests).
 *
 * The rules mirror llm-mailroom `pipeline/review_resolve.py:plan_resolution`
 * (the producer is the source of truth):
 *  - approve_as_is / correct archive the PARKED fields (plus field_corrections)
 *    and cannot change the class: a moved doc_type / subtype / subclass is
 *    resolution=reclassify, which re-extracts and takes no field_corrections;
 *  - field_corrections are MERGED over the parked fields, so a key the reviewer
 *    removed from the JSON only reaches the producer as an explicit null (the
 *    producer has no delete: it clears an optional field, and its schema check
 *    refuses a required or list field such as keywords, parties or confidence);
 *  - extracted_data is refused with any resolution, so it is only ever sent
 *    for the legacy Complete (no resolution), which replaces the extraction.
 */
"use strict";

var ReviewPlan = (() => {
  function isPublic(key) {
    return !String(key).startsWith("_");
  }

  function hasOwn(obj, key) {
    return Object.prototype.hasOwnProperty.call(obj, key);
  }

  /* Reviewer edits as producer field_corrections. `parked` is the diff base
   * (the public parked fields); null/undefined means "unknown", so every key
   * of `next` is an edit. A parked key missing from `next` is a deletion,
   * sent as null; `_`-prefixed keys are producer bookkeeping and never sent.
   * A non-object `next` (blank textarea) yields no edits, never deletions. */
  function fieldEdits(parked, next) {
    if (!next || typeof next !== "object" || Array.isArray(next)) return {};
    const base = parked && typeof parked === "object" ? parked : null;
    const edits = {};
    for (const key of Object.keys(next)) {
      if (!isPublic(key)) continue;
      if (!base || JSON.stringify(base[key]) !== JSON.stringify(next[key])) edits[key] = next[key];
    }
    if (base) {
      for (const key of Object.keys(base)) {
        if (!isPublic(key) || hasOwn(next, key)) continue;
        if (base[key] !== null && base[key] !== undefined) edits[key] = null;
      }
    }
    return edits;
  }

  function parseParked(raw) {
    if (!raw) return null;
    try {
      const value = JSON.parse(raw);
      return value && typeof value === "object" && !Array.isArray(value) ? value : null;
    } catch (_err) {
      return null;
    }
  }

  /* An empty select value ("(keep current)" doc type, "(none / keep)" subtype)
   * means "unchanged": the visualizer's review_actions drops it from the request,
   * so the producer sees no move. Only a non-empty, different value is a move. */
  function classMoved(docType, docSubclass, baseType, baseSub) {
    return (!!docType && docType !== (baseType || ""))
      || (!!docSubclass && docSubclass !== (baseSub || ""));
  }

  /* Decide what to send for one submit.
   *   input:  { resolution, disposition, docType, docSubclass, baseType, baseSub,
   *             rawExtracted, parkedRaw }
   *   output: { error } | { resolution, corrections, extractedData }
   * `resolution` is the clicked button's ("" for Re-extract / Complete / Requeue). */
  function plan(input) {
    const clicked = input.resolution || "";
    const disposition = input.disposition || "resume";
    const raw = String(input.rawExtracted || "");
    const moved = classMoved(input.docType, input.docSubclass, input.baseType, input.baseSub);
    const archives = clicked === "approve_as_is" || clicked === "correct";
    let resolution = clicked;
    let corrections;
    let extractedData;

    // The parked fields belong to the old class: the producer requires
    // reclassify (it re-extracts under the chosen one).
    if (archives && moved) resolution = "reclassify";

    if (raw.trim() || clicked === "correct" || disposition === "complete") {
      try {
        extractedData = raw.trim() ? JSON.parse(raw) : undefined;
      } catch (_err) {
        return { error: "extracted_data is not valid JSON" };
      }
      if (extractedData && (typeof extractedData !== "object" || Array.isArray(extractedData))) {
        return { error: "extracted_data must be a JSON object" };
      }
      if (archives) {
        // Only the reviewer's edits travel as field_corrections; the producer
        // merges them over the parked fields. Approve as-is with an edited
        // textarea is a correction, not a silent no-op.
        const edits = fieldEdits(parseParked(input.parkedRaw), extractedData);
        const edited = Object.keys(edits).length > 0;
        if (moved) {
          if (edited) {
            return {
              error: "The class changed, so the document is re-extracted and field edits cannot "
                + "be sent with it — reset the fields, or correct them after the class change.",
            };
          }
        } else if (clicked === "correct" || edited) {
          if (!edited) return { error: "No field changes to send — use Approve as-is." };
          corrections = edits;
          resolution = "correct";
        }
      }
      if (disposition === "complete" && (!extractedData || !Object.keys(extractedData).length)) {
        return { error: "Complete needs an extracted_data JSON object" };
      }
    }
    return { resolution, corrections, extractedData };
  }

  return { fieldEdits, parseParked, classMoved, plan };
})();

if (typeof module !== "undefined") module.exports = ReviewPlan;
if (typeof window !== "undefined") window.ReviewPlan = ReviewPlan;
