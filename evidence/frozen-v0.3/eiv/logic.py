"""Transparent exhaustive evaluator for a small, closed finite domain.

All claims are relative to the supplied vocabulary, facts, rules, constraints,
domain, and query. Enumeration order is stable and includes complete models.
"""

from itertools import product
import re


NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DEFAULT_MAX_ATOMS = 12
DEFAULT_MAX_ASSIGNMENTS = 1 << DEFAULT_MAX_ATOMS


class ValidationError(ValueError):
    pass


def _list(value, label):
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list")
    return value


def _name(value, label):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValidationError(f"{label} must be an identifier")
    return value


def _atom(atom, vocabulary, domain, allowed_vars):
    if not isinstance(atom, dict) or set(atom) != {"pred", "args"}:
        raise ValidationError("atom must contain exactly pred and args")
    pred = _name(atom["pred"], "predicate")
    if pred not in vocabulary:
        raise ValidationError(f"undeclared predicate: {pred}")
    args = _list(atom["args"], "atom.args")
    if len(args) != vocabulary[pred]:
        raise ValidationError(f"arity mismatch for {pred}")
    for arg in args:
        if not isinstance(arg, str):
            raise ValidationError("atom arguments must be strings")
        if arg.startswith("?"):
            if arg not in allowed_vars:
                raise ValidationError(f"unbound variable: {arg}")
        elif arg not in domain:
            raise ValidationError(f"constant outside domain: {arg}")


def _expr(expr, vocabulary, domain, allowed_vars, depth=0):
    if depth > 20 or not isinstance(expr, dict) or len(expr) != 1:
        raise ValidationError("expression must have one operator and depth <= 20")
    op, value = next(iter(expr.items()))
    if op == "atom":
        _atom(value, vocabulary, domain, allowed_vars)
    elif op == "not":
        _expr(value, vocabulary, domain, allowed_vars, depth + 1)
    elif op in ("and", "or"):
        if len(_list(value, op)) < 2:
            raise ValidationError(f"{op} requires at least two expressions")
        for child in value:
            _expr(child, vocabulary, domain, allowed_vars, depth + 1)
    elif op in ("implies", "iff"):
        if len(_list(value, op)) != 2:
            raise ValidationError(f"{op} requires two expressions")
        for child in value:
            _expr(child, vocabulary, domain, allowed_vars, depth + 1)
    else:
        raise ValidationError(f"unsupported operator: {op}")


def validate_spec(spec):
    """Validate an explicit model; return its ordered ground atoms."""
    if not isinstance(spec, dict) or set(spec) != {
        "domain", "vocabulary", "facts", "rules", "assumptions", "constraints", "query"
    }:
        raise ValidationError("spec requires domain, vocabulary, facts, rules, assumptions, constraints, query")
    domain = _list(spec["domain"], "domain")
    if not 1 <= len(domain) <= 4:
        raise ValidationError("domain requires 1-4 distinct constants")
    for constant in domain:
        _name(constant, "domain constant")
    if len(set(domain)) != len(domain):
        raise ValidationError("domain requires 1-4 distinct constants")
    vocab = spec["vocabulary"]
    if not isinstance(vocab, dict) or not 1 <= len(vocab) <= 16:
        raise ValidationError("vocabulary requires 1-16 predicates")
    for pred, arity in vocab.items():
        _name(pred, "predicate")
        if type(arity) is not int or not 0 <= arity <= 3:
            raise ValidationError("predicate arity must be 0-3")
    facts = _list(spec["facts"], "facts")
    rules = _list(spec["rules"], "rules")
    assumptions = _list(spec["assumptions"], "assumptions")
    constraints = _list(spec["constraints"], "constraints")
    if len(facts) + len(rules) + len(assumptions) + len(constraints) > 64:
        raise ValidationError("at most 64 assertions are supported")
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) != {"pred", "args", "value"}:
            raise ValidationError("fact requires exactly pred, args, value")
        if type(fact["value"]) is not bool:
            raise ValidationError("fact.value must be boolean")
        _atom({"pred": fact["pred"], "args": fact["args"]}, vocab, domain, set())
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"vars", "if", "then"}:
            raise ValidationError("rule requires exactly vars, if, then")
        variables = _list(rule["vars"], "rule.vars")
        if len(variables) > 3:
            raise ValidationError("rule requires at most three distinct variables")
        for var in variables:
            if not isinstance(var, str) or not var.startswith("?"):
                raise ValidationError("rule variables must begin with ?")
            _name(var[1:], "rule variable")
        if len(variables) != len(set(variables)):
            raise ValidationError("rule variables must be distinct")
        _expr(rule["if"], vocab, domain, set(variables))
        _expr(rule["then"], vocab, domain, set(variables))
    assumption_ids = []
    for assumption in assumptions:
        if not isinstance(assumption, dict) or set(assumption) != {"id", "formula"}:
            raise ValidationError("assumption requires id and formula")
        assumption_ids.append(_name(assumption["id"], "assumption id"))
        _expr(assumption["formula"], vocab, domain, set())
    if len(assumption_ids) != len(set(assumption_ids)):
        raise ValidationError("assumption ids must be unique")
    for constraint in constraints:
        _expr(constraint, vocab, domain, set())
    _expr(spec["query"], vocab, domain, set())
    return [(pred, args) for pred, arity in sorted(vocab.items())
            for args in product(domain, repeat=arity)]


def _eval(expr, bits, positions, env):
    op, value = next(iter(expr.items()))
    if op == "atom":
        key = (value["pred"], tuple(env.get(arg, arg) for arg in value["args"]))
        return bool(bits & (1 << positions[key]))
    if op == "not":
        return not _eval(value, bits, positions, env)
    if op == "and":
        return all(_eval(child, bits, positions, env) for child in value)
    if op == "or":
        return any(_eval(child, bits, positions, env) for child in value)
    a = _eval(value[0], bits, positions, env)
    b = _eval(value[1], bits, positions, env)
    return (not a or b) if op == "implies" else a == b


def _compiled(spec, atoms):
    positions = {key: index for index, key in enumerate(atoms)}
    facts = [((fact["pred"], tuple(fact["args"])), fact["value"])
             for fact in spec["facts"]]
    ground_rules = []
    for rule in spec["rules"]:
        for values in product(spec["domain"], repeat=len(rule["vars"])):
            ground_rules.append((rule["if"], rule["then"], dict(zip(rule["vars"], values))))
    return positions, facts, ground_rules


def _satisfies(spec, bits, compiled):
    positions, facts, ground_rules = compiled
    for key, expected in facts:
        if bool(bits & (1 << positions[key])) != expected:
            return False
    for premise, consequence, env in ground_rules:
        if _eval(premise, bits, positions, env) and not _eval(consequence, bits, positions, env):
            return False
    return (all(_eval(item["formula"], bits, positions, {}) for item in spec["assumptions"])
            and all(_eval(formula, bits, positions, {}) for formula in spec["constraints"]))


def _label(key):
    pred, args = key
    return pred + ("(" + ",".join(args) + ")" if args else "")


def _world(bits, atoms):
    return {_label(key): bool(bits & (1 << index)) for index, key in enumerate(atoms)}


def evaluate_world(spec, world):
    """Independently inspect a returned complete assignment in tests or clients."""
    atoms = validate_spec(spec)
    names = [_label(key) for key in atoms]
    if not isinstance(world, dict) or set(world) != set(names) or any(type(v) is not bool for v in world.values()):
        raise ValidationError("world must assign every ground atom exactly once")
    bits = sum(1 << i for i, name in enumerate(names) if world[name])
    compiled = _compiled(spec, atoms)
    return {"satisfies_theory": _satisfies(spec, bits, compiled),
            "query_value": _eval(spec["query"], bits, compiled[0], {})}


def analyze_spec(spec, max_atoms=DEFAULT_MAX_ATOMS, max_assignments=DEFAULT_MAX_ASSIGNMENTS):
    """Classify by checking satisfiability of T∧q and T∧¬q."""
    atoms = validate_spec(spec)
    if type(max_atoms) is not int or type(max_assignments) is not int or max_atoms < 1 or max_assignments < 1:
        raise ValidationError("resource limits must be positive integers")
    assignments = 1 << len(atoms)
    if len(atoms) > max_atoms or assignments > max_assignments:
        return {"status": "unknown", "reason": "resource_limit", "ground_atoms": len(atoms),
                "assumption_ids": [item["id"] for item in spec["assumptions"]],
                "assignments_required": assignments, "assignments_examined": 0,
                "theory_models": None, "sat_theory_and_query": None,
                "sat_theory_and_not_query": None, "witness_query": None,
                "countermodel": None}
    compiled = _compiled(spec, atoms)
    witness_yes = witness_no = None
    theory_models = 0
    for bits in range(assignments):
        if not _satisfies(spec, bits, compiled):
            continue
        theory_models += 1
        if _eval(spec["query"], bits, compiled[0], {}):
            if witness_yes is None:
                witness_yes = _world(bits, atoms)
        elif witness_no is None:
            witness_no = _world(bits, atoms)
    sat_yes, sat_no = witness_yes is not None, witness_no is not None
    status = ("inconsistent" if not sat_yes and not sat_no else
              "underdetermined" if sat_yes and sat_no else
              "entailed" if sat_yes else "refuted")
    return {"status": status, "ground_atoms": len(atoms),
            "assumption_ids": [item["id"] for item in spec["assumptions"]],
            "assignments_required": assignments, "assignments_examined": assignments,
            "theory_models": theory_models, "sat_theory_and_query": sat_yes,
            "sat_theory_and_not_query": sat_no, "witness_query": witness_yes,
            "countermodel": witness_no}
