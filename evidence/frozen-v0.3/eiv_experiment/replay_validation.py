"""Additional bundle integrity checks, without changing the frozen v1 prompts.

This validates evidence structure and access logs; it cannot attest that a model
actually executed unless provider/runtime provenance is independently trusted.
"""
from __future__ import annotations

import hashlib
import json
import math

from .replay import ARMS, oracle_disclosure, public_packet, validate_replay


def validate_bundle(records, cases):
    validate_replay(records, cases)
    by_id = {case["case_id"]: case for case in cases}
    models = {(row["model"], row["model_digest"]) for row in records}
    if len(models) != 1:
        raise ValueError("matched comparison requires one shared model and immutable digest")
    settings = set()
    for row in records:
        case = by_id[row["case_id"]]
        packet = public_packet(case)
        packet_hash = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
        if row.get("initial_packet_sha256") != packet_hash:
            raise ValueError("initial packet hash differs from label-free benchmark input")
        if not math.isfinite(row["latency_seconds"]):
            raise ValueError("latency must be finite")
        cost = row.get("monetary_cost_usd")
        if cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost)):
            raise ValueError("cost must be a finite amount or null for unknown")
        raw = row["raw_messages"]
        if len(raw) != row["usage"]["calls"]:
            raise ValueError("raw call count differs from usage")
        first = raw[0].get("request", {})
        messages = first.get("messages", [])
        users = [message for message in messages if message.get("role") == "user"]
        if len(users) != 1:
            raise ValueError("initial primary-arm request must have exactly one public user packet")
        try:
            initial = json.loads(users[0]["content"])
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError("missing initial public JSON packet") from error
        if initial != packet:
            raise ValueError("raw initial prompt differs from public input; possible label leakage")
        if first.get("model") != row["model"]:
            raise ValueError("recorded model differs from raw request")
        for call in raw:
            request = call.get("request", {})
            if request.get("model") != row["model"]:
                raise ValueError("model changed within a case")
            options = request.get("options")
            if not isinstance(options, dict):
                raise ValueError("raw model settings required")
            settings.add(json.dumps(options, sort_keys=True))
            response = call.get("response")
            token_count = response.get("eval_count") if isinstance(response, dict) else None
            if token_count is not None and (type(token_count) is not int or not 0 <= token_count <= 1800):
                raise ValueError("per-call output cap exceeded")
        for access in row["oracle_access"]:
            if access.get("mode") != "full_intent_disclosure" or access.get("answer") != oracle_disclosure(case, 0):
                raise ValueError("oracle access differs from frozen full-intent response")
    if len(settings) != 1:
        raise ValueError("matched comparison requires identical recorded model settings")
    return {"records": len(records), "cases": len(cases), "arms": list(ARMS),
            "model": next(iter(models))[0], "integrity": "validated; does not attest actual model execution"}
