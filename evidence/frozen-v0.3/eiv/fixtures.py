"""Deterministic, manually formalized examples and benchmark cases."""


def atom(pred, *args):
    return {"atom": {"pred": pred, "args": list(args)}}


def fact(pred, value=True, *args):
    return {"pred": pred, "args": list(args), "value": value}


def rule(variables, premise, consequence):
    return {"vars": list(variables), "if": premise, "then": consequence}


def spec(domain, vocabulary, facts, rules, constraints, query, assumptions=None):
    return {"domain": domain, "vocabulary": vocabulary, "facts": facts,
            "rules": rules, "assumptions": assumptions or [],
            "constraints": constraints, "query": query}


def candidate(candidate_id, interpretation, model):
    return {"id": candidate_id, "interpretation": interpretation, "spec": model}


def case(title, candidates, questions=None):
    return {"title": title, "source_type": "manually_formalized_fixture",
            "candidates": candidates, "questions": questions or []}


def item(identifier, split, prompt, formal_case, oracle):
    return {"id": identifier, "split": split, "illustrative_request": prompt,
            "case": formal_case, "oracle_spec": oracle}


def build_suite():
    """Return cases; oracle specs are for evaluation only, never for inference."""
    suite = []
    membership_vocab = {"Member": 1, "Paid": 1}
    member_query = atom("Member", "Ana")
    necessary = spec(["Ana"], membership_vocab, [fact("Paid", True, "Ana")],
                     [rule(["?x"], atom("Member", "?x"), atom("Paid", "?x"))], [], member_query)
    sufficient = spec(["Ana"], membership_vocab, [fact("Paid", True, "Ana")],
                      [rule(["?x"], atom("Paid", "?x"), atom("Member", "?x"))], [], member_query)
    suite.append(item("necessary_vs_sufficient", "development",
        "Ana has paid. Paying is required for membership / paying makes someone a member. Is Ana a member?",
        case("Necessary versus sufficient membership",
            [candidate("necessary", "Membership implies payment; payment alone may not grant membership.", necessary),
             candidate("sufficient", "Payment implies membership.", sufficient)],
            [{"id": "payment_rule", "prompt": "Does paying by itself guarantee membership?",
              "answers": [{"id": "yes", "label": "Yes, payment is sufficient", "retain": ["sufficient"]},
                          {"id": "no", "label": "No, payment is only necessary", "retain": ["necessary"]}]}]),
        sufficient))

    suite.append(item("missing_fact", "development",
        "Membership requires payment; Ana has paid. Is Ana a member?",
        case("Missing membership fact", [candidate("necessary", "Only a necessary condition is supplied.", necessary)]),
        necessary))

    contradiction = spec(["Ana"], {"Approved": 1},
                         [fact("Approved", True, "Ana"), fact("Approved", False, "Ana")],
                         [], [], atom("Approved", "Ana"))
    suite.append(item("contradiction", "development",
        "Ana is approved and Ana is not approved. Is Ana approved?",
        case("Contradictory facts", [candidate("literal", "Both assertions are included.", contradiction)]),
        contradiction))

    irrelevant_yes = spec(["Ana"], {"Paid": 1, "Tax": 1},
                          [fact("Paid", True, "Ana")],
                          [], [], atom("Paid", "Ana"),
                          [{"id": "TaxApplies", "formula": atom("Tax", "Ana")}])
    irrelevant_no = spec(["Ana"], {"Paid": 1, "Tax": 1},
                         [fact("Paid", True, "Ana")],
                         [], [], atom("Paid", "Ana"),
                         [{"id": "TaxDoesNotApply", "formula": {"not": atom("Tax", "Ana")}}])
    suite.append(item("irrelevant_ambiguity", "development",
        "Ana paid. A separate tax statement is ambiguous. Did Ana pay?",
        case("Irrelevant ambiguity",
             [candidate("tax_yes", "Tax applied.", irrelevant_yes),
              candidate("tax_no", "Tax did not apply.", irrelevant_no)],
             [{"id": "tax", "prompt": "Was the tax applied?",
               "answers": [{"id": "yes", "label": "Yes", "retain": ["tax_yes"]},
                           {"id": "no", "label": "No", "retain": ["tax_no"]}]}]),
        irrelevant_yes))

    inconsistent_candidate = spec(["Ana"], {"Member": 1},
                                  [fact("Member", True, "Ana"), fact("Member", False, "Ana")],
                                  [], [], atom("Member", "Ana"))
    consistent_candidate = spec(["Ana"], {"Member": 1},
                                [fact("Member", True, "Ana")], [], [], atom("Member", "Ana"))
    suite.append(item("inconsistent_candidate", "development",
        "One reading includes both membership and nonmembership; another treats the latter as a typo.",
        case("Visible inconsistent candidate",
             [candidate("literal", "Keep both contradictory statements.", inconsistent_candidate),
              candidate("typo", "The negative statement was a typo.", consistent_candidate)],
             [{"id": "typo", "prompt": "Was the negative membership statement a typo?",
               "answers": [{"id": "yes", "label": "Yes", "retain": ["typo"]},
                           {"id": "no", "label": "No", "retain": ["literal"]}]}]),
        consistent_candidate))

    coverage_vocab = {"Approved": 1, "Member": 1, "Paid": 1}
    coverage_q = atom("Member", "Ana")
    wrong_a = spec(["Ana"], coverage_vocab, [fact("Member", True, "Ana")], [], [], coverage_q)
    wrong_b = spec(["Ana"], coverage_vocab, [fact("Paid", True, "Ana")],
                   [rule(["?x"], atom("Paid", "?x"), atom("Member", "?x"))], [], coverage_q)
    intended = spec(["Ana"], coverage_vocab, [fact("Approved", False, "Ana")],
                    [rule(["?x"], atom("Member", "?x"), atom("Approved", "?x"))], [], coverage_q)
    suite.append(item("candidate_coverage_failure", "structural_holdout",
        "Ana paid, but membership requires approval and Ana was not approved. Is Ana a member?",
        case("Candidate coverage failure",
             [candidate("asserted_member", "Incorrectly treats payment as a membership assertion.", wrong_a),
              candidate("payment_suffices", "Incorrectly treats payment as sufficient.", wrong_b)]),
        intended))

    p = atom("P", "Ana")
    suite.append(item("simple_entailed", "development", "P(Ana). Does P(Ana) hold?",
        case("Direct positive fact", [candidate("literal", "The fact is asserted.",
            spec(["Ana"], {"P": 1}, [fact("P", True, "Ana")], [], [], p))]),
        spec(["Ana"], {"P": 1}, [fact("P", True, "Ana")], [], [], p)))
    suite.append(item("simple_refuted", "development", "Not P(Ana). Does P(Ana) hold?",
        case("Direct negative fact", [candidate("literal", "The negative fact is asserted.",
            spec(["Ana"], {"P": 1}, [fact("P", False, "Ana")], [], [], p))]),
        spec(["Ana"], {"P": 1}, [fact("P", False, "Ana")], [], [], p)))

    # Structural holdout: disjunction, two-hop deduction, and contraposition.
    ab_vocab = {"A": 0, "B": 0}
    disjunction = {"or": [atom("A"), atom("B")]}
    disj_entailed = spec(["Unit"], ab_vocab, [fact("A", False)], [], [disjunction], atom("B"))
    disj_unknown = spec(["Unit"], ab_vocab, [], [], [disjunction], atom("A"))
    suite.append(item("holdout_disjunction_entailed", "structural_holdout",
        "A or B; not A. Is B true?",
        case("Disjunctive entailment", [candidate("literal", "Inclusive disjunction.", disj_entailed)]),
        disj_entailed))
    suite.append(item("holdout_disjunction_underdetermined", "structural_holdout",
        "A or B. Is A true?",
        case("Disjunctive uncertainty", [candidate("literal", "Inclusive disjunction.", disj_unknown)]),
        disj_unknown))
    chain = spec(["Ana"], {"P": 1, "Q": 1, "R": 1}, [fact("P", True, "Ana")],
                 [rule(["?x"], atom("P", "?x"), atom("Q", "?x")),
                  rule(["?x"], atom("Q", "?x"), atom("R", "?x"))], [], atom("R", "Ana"))
    suite.append(item("holdout_two_hop", "structural_holdout",
        "P implies Q and Q implies R; P(Ana). Is R(Ana) true?",
        case("Two hop deduction", [candidate("literal", "Both rules are universal.", chain)]), chain))
    contrapositive = spec(["Ana"], {"P": 1, "Q": 1}, [fact("Q", False, "Ana")],
                         [rule(["?x"], atom("P", "?x"), atom("Q", "?x"))], [], atom("P", "Ana"))
    suite.append(item("holdout_contrapositive", "structural_holdout",
        "P implies Q; Q(Ana) is false. Is P(Ana) true?",
        case("Contrapositive deduction", [candidate("literal", "The rule is universal.", contrapositive)]),
        contrapositive))
    return suite
