from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pathlex.models import StorySpec, StoryStatus
from pathlex.planner import plan_story


GENERATOR_VERSION = "pathlex-spec-builder-1.0.0"
GLOBAL_SEED = 2026112101
SCENARIO_COUNTS = {
    "easy": 6,
    "tail_risk": 6,
    "standard": 3,
    "ambiguous": 2,
    "hard": 3,
}


def _entry(
    lemma: str,
    sense: str,
    part_of_speech: str,
    collocation: str,
    positive: str,
    negative: str,
) -> dict[str, Any]:


    return {
        "lemma": lemma,
        "sense": sense,
        "part_of_speech": part_of_speech,
        "allowed_collocations": [collocation],
        "forbidden_patterns": [f"metalinguistic mention of {lemma}"],
        "positive_examples": [positive],
        "negative_examples": [negative],
    }


LEXICAL_BANK: dict[str, list[dict[str, Any]]] = {
    "A1": [
        _entry("borrow", "take and use something temporarily, then return it", "verb", "borrow a map", "Lina asked to borrow a map for the walk.", "The sign displayed the word borrow without using its meaning."),
        _entry("choose", "select one option from two or more", "verb", "choose a path", "We must choose a path before sunset.", "The guide called the path a choose."),
        _entry("carry", "hold and move something from one place to another", "verb", "carry a bag", "Omar will carry a bag to the station.", "The music carried well across the hall."),
        _entry("invite", "ask someone to come or take part", "verb", "invite a friend", "Mia decided to invite a friend to the picnic.", "The empty room looked invite."),
        _entry("quiet", "making little or no noise", "adjective", "a quiet room", "They found a quiet room to read in.", "Kai quieted the alarm quickly."),
        _entry("early", "before the expected or usual time", "adverb", "arrive early", "We should arrive early for the train.", "They ate an early made of fruit."),
        _entry("follow", "go behind or along the route shown by someone or something", "verb", "follow the signs", "Please follow the signs to the garden.", "The blue follow was on the wall."),
        _entry("return", "go or come back to a place", "verb", "return home", "They will return home after the game.", "The shop gave a return of five coins."),
        _entry("safe", "not likely to cause harm or danger", "adjective", "a safe route", "The bridge is a safe route across the stream.", "She put the letter in a safe."),
        _entry("share", "let another person use or have part of something", "verb", "share some food", "Noah offered to share some food with Ana.", "The company sold a share yesterday."),
        _entry("wait", "stay until an expected event or person arrives", "verb", "wait for the bus", "We can wait for the bus near the library.", "The box had a heavy wait."),
        _entry("help", "make it easier for someone to do something", "verb", "help a visitor", "Tariq stopped to help a visitor read the map.", "The soup tasted help."),
        _entry("near", "at a short distance from a place or thing", "preposition", "near the gate", "The bicycle is near the gate.", "They nearly the gate at noon."),
        _entry("ready", "prepared for an activity or event", "adjective", "ready to leave", "Everyone was ready to leave at nine.", "She readied as a blue notebook."),
        _entry("remember", "keep or bring a fact or event back to mind", "verb", "remember the code", "Please remember the code for the door.", "The old statue was a remember."),
        _entry("different", "not the same as another thing", "adjective", "a different answer", "Leo gave a different answer to the question.", "They different the two bags carefully."),
        _entry("careful", "giving attention in order to avoid a mistake or danger", "adjective", "be careful", "Be careful when you cross the wet floor.", "She careful carried the glass."),
        _entry("decide", "make a choice after thinking", "verb", "decide to stay", "They decide to stay until the rain stops.", "The decide was printed in red."),
    ],
    "B1": [
        _entry("navigate", "find and follow a route through a place", "verb", "navigate the trail", "The team used landmarks to navigate the trail.", "The website menu was easy to navigate, but no physical route was involved."),
        _entry("resolve", "find a satisfactory solution to a problem", "verb", "resolve a conflict", "The two groups met to resolve a conflict about the route.", "The camera can resolve fine details in low light."),
        _entry("estimate", "judge an amount or value approximately", "verb", "estimate the distance", "Priya tried to estimate the distance to the tower.", "The final estimate was used as a verb object incorrectly."),
        _entry("maintain", "keep something in a good or continuing condition", "verb", "maintain the equipment", "Volunteers maintain the equipment after every trip.", "The witness maintained that the story was true."),
        _entry("observe", "watch something carefully", "verb", "observe the pattern", "We stopped to observe the pattern of lights.", "The town will observe the holiday on Monday."),
        _entry("recommend", "suggest that something is suitable", "verb", "recommend a route", "The ranger will recommend a route for beginners.", "The notice was a recommend near the desk."),
        _entry("avoid", "stay away from or prevent contact with something", "verb", "avoid the traffic", "We left early to avoid the traffic downtown.", "The empty space was an avoid."),
        _entry("confirm", "establish that something is true or correct", "verb", "confirm the booking", "Call the hostel to confirm the booking.", "The music confirmed the room with sound."),
        _entry("compare", "examine things to identify similarities or differences", "verb", "compare two options", "They compare two options before choosing.", "The compare was stored in a drawer."),
        _entry("respond", "say or do something as an answer or reaction", "verb", "respond to a request", "Please respond to the request by Friday.", "They bought a respond at the market."),
        _entry("require", "need something for a particular purpose", "verb", "require permission", "This route will require permission from the park office.", "The sign was very require."),
        _entry("available", "able to be used or obtained", "adjective", "tickets are available", "Extra tickets are available at the front desk.", "The clerk availabled two seats."),
        _entry("reliable", "consistently dependable or accurate", "adjective", "a reliable source", "Use a reliable source to check the timetable.", "The machine reliabled all night."),
        _entry("challenge", "a difficult task that tests ability", "noun", "face a challenge", "Crossing the valley will be a challenge for the group.", "They challenge was carefully packed."),
        _entry("notice", "become aware of something", "verb", "notice a change", "Did you notice a change in the weather?", "The office posted a notice about closing time."),
        _entry("protect", "keep someone or something safe from harm", "verb", "protect the habitat", "The new fence will protect the habitat from damage.", "The helmet was a protect."),
        _entry("prepare", "make ready for a future activity", "verb", "prepare for the trip", "We met to prepare for the trip on Saturday.", "The prepare looked blue."),
        _entry("suggest", "put forward an idea for consideration", "verb", "suggest an alternative", "Ella will suggest an alternative if the road closes.", "They bought a suggest at the station."),
    ],
    "B2": [
        _entry("mitigate", "make a harmful effect less severe", "verb", "mitigate the risk", "The revised route should mitigate the risk of flooding.", "The committee mitigated the map on the table."),
        _entry("allocate", "distribute resources for a particular purpose", "verb", "allocate resources", "The coordinator will allocate resources to each team.", "The map allocated toward the river by itself."),
        _entry("infer", "reach a conclusion from evidence rather than direct statement", "verb", "infer from evidence", "We can infer from the tracks that an animal passed recently.", "The guide inferred the supplies into three boxes."),
        _entry("sustain", "keep an activity or process continuing over time", "verb", "sustain the effort", "Short breaks helped the team sustain the effort.", "The rope sustained under the shelf as a location."),
        _entry("verify", "check that something is accurate or true", "verb", "verify the claim", "Use the original record to verify the claim.", "The claim was a verify in the folder."),
        _entry("ambiguous", "open to more than one reasonable interpretation", "adjective", "an ambiguous instruction", "The ambiguous instruction caused the groups to choose different doors.", "They ambiguous the message before lunch."),
        _entry("coherent", "logical, consistent, and easy to understand as a whole", "adjective", "a coherent explanation", "Jin gave a coherent explanation of the plan.", "The group coherent the notes."),
        _entry("prioritize", "decide which tasks are most important and deal with them first", "verb", "prioritize urgent tasks", "The team must prioritize urgent tasks before decorating the room.", "The schedule was a prioritize."),
        _entry("constraint", "a limitation that restricts possible choices", "noun", "a time constraint", "A time constraint forced them to take the shorter route.", "They constraint the supplies each morning."),
        _entry("compensate", "make up for a loss, weakness, or disadvantage", "verb", "compensate for a delay", "They walked faster to compensate for a delay.", "The delay compensated into the bag."),
        _entry("evaluate", "judge quality or value using stated criteria", "verb", "evaluate the options", "The committee will evaluate the options against four criteria.", "The report was an evaluate."),
        _entry("plausible", "seeming reasonable or likely to be true", "adjective", "a plausible explanation", "Her account offered a plausible explanation for the missing key.", "They plausibled the route."),
        _entry("subsequent", "coming after something else in time or order", "adjective", "a subsequent review", "A subsequent review found an error in the first plan.", "They subsequent the first report."),
        _entry("integrate", "combine parts so that they work together", "verb", "integrate the evidence", "The group will integrate the evidence into one proposal.", "The evidence was an integrate."),
        _entry("discrepancy", "an unexpected difference between things that should agree", "noun", "identify a discrepancy", "Mara identified a discrepancy between the two schedules.", "They discrepancy the route at noon."),
        _entry("feasible", "possible and practical under the given conditions", "adjective", "a feasible solution", "The shorter bridge is a feasible solution within the budget.", "The engineers feasibled the bridge."),
        _entry("accountable", "responsible for decisions and expected to explain them", "adjective", "be accountable for", "Each leader is accountable for the safety check.", "They accountable the equipment."),
        _entry("contingency", "an event that may occur and requires a backup plan", "noun", "a contingency plan", "They prepared a contingency plan for heavy rain.", "The team contingency the map."),
    ],
}


THEMES: list[dict[str, Any]] = [
    {"id": "city_map", "title": "The Missing City Map", "theme": "finding a safe route through a city district", "contexts": ["route planning", "street decision", "arrival reflection"]},
    {"id": "garden_opening", "title": "Opening the Community Garden", "theme": "preparing a community garden for visitors", "contexts": ["preparation", "team decision", "visitor feedback"]},
    {"id": "museum_clue", "title": "The Museum Clue Trail", "theme": "following clues in a local museum", "contexts": ["clue inspection", "choice point", "solution review"]},
    {"id": "island_ferry", "title": "The Last Island Ferry", "theme": "reaching an island ferry before departure", "contexts": ["timetable check", "route choice", "journey review"]},
    {"id": "library_event", "title": "A Night at the Library", "theme": "organizing an evening reading event", "contexts": ["event planning", "resource choice", "event reflection"]},
    {"id": "forest_station", "title": "The Forest Research Station", "theme": "delivering supplies to a forest station", "contexts": ["supply planning", "trail decision", "delivery review"]},
    {"id": "market_project", "title": "The Weekend Market Project", "theme": "setting up a small community market", "contexts": ["stall planning", "customer decision", "market reflection"]},
    {"id": "coastal_walk", "title": "The Coastal Walk", "theme": "planning a responsible coastal walk", "contexts": ["weather planning", "path decision", "impact reflection"]},
    {"id": "school_exhibit", "title": "The Science Exhibit", "theme": "building a public science exhibit", "contexts": ["design planning", "evidence decision", "exhibit review"]},
    {"id": "train_connection", "title": "The Train Connection", "theme": "making a difficult train connection", "contexts": ["schedule planning", "platform decision", "arrival reflection"]},
    {"id": "river_cleanup", "title": "The River Cleanup", "theme": "coordinating a safe river cleanup", "contexts": ["task planning", "safety decision", "impact review"]},
    {"id": "festival_stage", "title": "The Festival Stage", "theme": "preparing a stage for a neighborhood festival", "contexts": ["resource planning", "schedule choice", "performance review"]},
    {"id": "mountain_shelter", "title": "The Mountain Shelter", "theme": "reaching and preparing a mountain shelter", "contexts": ["equipment check", "trail decision", "shelter reflection"]},
    {"id": "history_archive", "title": "The Archive Mystery", "theme": "checking records to solve a local history question", "contexts": ["record inspection", "evidence choice", "finding review"]},
    {"id": "robot_contest", "title": "The Robot Contest", "theme": "repairing a team robot before a contest", "contexts": ["fault diagnosis", "repair decision", "test review"]},
    {"id": "wetland_visit", "title": "The Wetland Visit", "theme": "planning a low-impact wetland visit", "contexts": ["access planning", "habitat decision", "visit reflection"]},
    {"id": "radio_broadcast", "title": "The Community Broadcast", "theme": "preparing a community radio report", "contexts": ["source planning", "editing decision", "broadcast review"]},
    {"id": "theater_prop", "title": "The Missing Theater Prop", "theme": "finding a missing prop before a performance", "contexts": ["search planning", "location choice", "performance reflection"]},
    {"id": "campus_tour", "title": "The Campus Tour", "theme": "designing an accessible campus tour", "contexts": ["route planning", "visitor choice", "tour reflection"]},
    {"id": "energy_plan", "title": "The Neighborhood Energy Plan", "theme": "selecting practical energy-saving changes", "contexts": ["evidence review", "priority decision", "plan reflection"]},
    {"id": "storm_response", "title": "After the Storm", "theme": "coordinating a neighborhood response after a storm", "contexts": ["needs assessment", "resource decision", "response review"]},
    {"id": "cafe_launch", "title": "The Pop-up Cafe", "theme": "launching a small pop-up cafe", "contexts": ["menu planning", "service decision", "customer review"]},
    {"id": "heritage_route", "title": "The Heritage Route", "theme": "designing a route through heritage sites", "contexts": ["site research", "route decision", "tour review"]},
    {"id": "water_system", "title": "The Village Water System", "theme": "reviewing options for a reliable water system", "contexts": ["evidence review", "design decision", "system reflection"]},
]


VOCABULARY = {
    "A1": {
        "known": ["go", "come", "look", "walk", "friend", "home", "time", "place", "day", "good", "small", "find"],
        "base": ["map", "road", "door", "food", "water", "train", "garden", "room", "book", "team", "start", "finish"],
    },
    "B1": {
        "known": ["route", "choice", "problem", "reason", "result", "plan", "information", "change", "support", "include", "continue", "possible"],
        "base": ["evidence", "schedule", "resource", "visitor", "equipment", "environment", "decision", "project", "condition", "solution", "review", "safety"],
    },
    "B2": {
        "known": ["alternative", "consequence", "interpret", "significant", "strategy", "consistent", "appropriate", "relevant", "capacity", "objective", "potential", "context"],
        "base": ["criterion", "trade-off", "implementation", "evidence", "framework", "priority", "assumption", "outcome", "resource", "restriction", "stakeholder", "revision"],
    },
}


def _stable_seed(*parts: int) -> int:
    value = GLOBAL_SEED
    for index, part in enumerate(parts, start=1):
        value = (value * 1_000_003 + part * (97 + index * 13)) % 2_147_483_647
    return value


def _target_payload(
    entry: dict[str, Any],
    *,
    target_id: str,
    contexts: list[str],
) -> dict[str, Any]:
    payload = copy.deepcopy(entry)
    payload.update(
        {
            "id": target_id,
            "min_occurrences": 3,
            "min_gap": 0,
            "max_gap": 1,
            "min_contexts": 2,
            "context_labels": list(contexts[:3]),
            "required_phases": ["opening", "middle", "ending"],
            "mode_requirements": {
                "exposure": 1,
                "judgment": 1,
                "retrieval": 1,
            },
            "weight": 1.0,
        }
    )
    return payload


def _make_spec(
    *,
    sample_id: str,
    split: str,
    cefr: str,
    target_count: int,
    terminal_paths: int,
    sequence: int,
    scenario_type: str,
    specification_seed: int,
    sentinel_type: str | None = None,
) -> dict[str, Any]:
    depth = 4 if terminal_paths == 8 else 5
    max_nodes = 15 if terminal_paths == 8 else 31
    rng = random.Random(specification_seed)
    theme = THEMES[(sequence + {"A1": 0, "B1": 7, "B2": 13}[cefr]) % len(THEMES)]
    chosen = rng.sample(LEXICAL_BANK[cefr], target_count)
    targets = [
        _target_payload(
            item,
            target_id=f"{sample_id}-LU{index:02d}",
            contexts=theme["contexts"],
        )
        for index, item in enumerate(chosen, start=1)
    ]
    if sentinel_type == "OCC_DEPTH_CONFLICT":
        targets[0]["min_occurrences"] = depth
    elif sentinel_type == "SPACING_CONFLICT":
        targets[0]["min_gap"] = 1
        targets[0]["max_gap"] = 1

    stratum = f"{cefr}_T{target_count:02d}_P{terminal_paths:02d}"
    row: dict[str, Any] = {
        "sample_id": sample_id,
        "id": sample_id,
        "split": split,
        "feasible_expected": sentinel_type is None,
        "stratum": stratum,
        "cefr_level": cefr,
        "target_count": target_count,
        "terminal_path_count": terminal_paths,
        "branch_factor": 2,
        "depth": depth,
        "max_paths": terminal_paths,
        "max_nodes": max_nodes,
        "common_prefix_max_ratio": 0.5,
        "title": f"{theme['title']} [{sample_id}]",
        "theme_id": theme["id"],
        "theme": theme["theme"],
        "known_vocabulary": list(VOCABULARY[cefr]["known"]),
        "base_vocabulary": list(VOCABULARY[cefr]["base"]),
        "targets": targets,
        "safety_constraints": [
            "No graphic violence or discriminatory content.",
            "Keep every choice age-appropriate and reversible within the story.",
        ],
        "interface_language": "en",
        "scenario_type": scenario_type,
        "specification_seed": specification_seed,
        "generator_version": GENERATOR_VERSION,
    }
    if sentinel_type is not None:
        row["sentinel_type"] = sentinel_type
        row["expected_reason_code"] = (
            "INSUFFICIENT_DISTINCT_DEPTHS"
            if sentinel_type == "OCC_DEPTH_CONFLICT"
            else "NO_DEPTH_COMBINATION_SATISFIES_CONSTRAINTS"
        )
    return row


def _strata() -> list[tuple[str, int, int]]:
    return [
        (cefr, target_count, terminal_paths)
        for cefr in ("A1", "B1", "B2")
        for target_count in (4, 8)
        for terminal_paths in (8, 16)
    ]


def build_final_test_specs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scenarios = [
        name
        for name, count in SCENARIO_COUNTS.items()
        for _ in range(count)
    ]
    for stratum_index, (cefr, target_count, terminal_paths) in enumerate(_strata()):
        assigned = list(scenarios)
        random.Random(_stable_seed(10, stratum_index)).shuffle(assigned)
        for cell_index, scenario in enumerate(assigned, start=1):
            sample_id = (
                f"M1-F-{cefr}-T{target_count:02d}-P{terminal_paths:02d}-{cell_index:03d}"
            )
            seed = _stable_seed(20, stratum_index, cell_index)
            rows.append(
                _make_spec(
                    sample_id=sample_id,
                    split="final_test",
                    cefr=cefr,
                    target_count=target_count,
                    terminal_paths=terminal_paths,
                    sequence=stratum_index * 20 + cell_index,
                    scenario_type=scenario,
                    specification_seed=seed,
                )
            )
    return rows


def build_sentinel_specs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stratum_index, (cefr, target_count, terminal_paths) in enumerate(_strata()):
        for sentinel_index, sentinel_type in enumerate(
            ("OCC_DEPTH_CONFLICT", "SPACING_CONFLICT"), start=1
        ):
            short = "OCC" if sentinel_type.startswith("OCC") else "GAP"
            sample_id = (
                f"M1-S-{cefr}-T{target_count:02d}-P{terminal_paths:02d}-{short}-{sentinel_index:02d}"
            )
            rows.append(
                _make_spec(
                    sample_id=sample_id,
                    split="sentinel",
                    cefr=cefr,
                    target_count=target_count,
                    terminal_paths=terminal_paths,
                    sequence=300 + stratum_index * 2 + sentinel_index,
                    scenario_type="boundary_sentinel",
                    specification_seed=_stable_seed(30, stratum_index, sentinel_index),
                    sentinel_type=sentinel_type,
                )
            )
    return rows


def build_pretest_specs(split: str, count: int, offset: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    strata = _strata()
    scenario_cycle = ("easy", "standard", "tail_risk", "ambiguous", "hard")
    prefix = "DEV" if split == "development" else "VAL"
    for index in range(count):
        cefr, target_count, terminal_paths = strata[(index * 5 + offset) % len(strata)]
        sample_id = f"M1-{prefix}-{cefr}-T{target_count:02d}-P{terminal_paths:02d}-{index + 1:03d}"
        rows.append(
            _make_spec(
                sample_id=sample_id,
                split=split,
                cefr=cefr,
                target_count=target_count,
                terminal_paths=terminal_paths,
                sequence=500 + offset * 100 + index,
                scenario_type=scenario_cycle[index % len(scenario_cycle)],
                specification_seed=_stable_seed(40 + offset, index),
            )
        )
    return rows


def _write_json(path: Path, payload: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    os.replace(temporary, path)


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
    os.replace(temporary, path)


def _verify(
    development: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    final_test: list[dict[str, Any]],
    sentinels: list[dict[str, Any]],
) -> dict[str, Any]:
    feasible_failures: list[dict[str, Any]] = []
    observed_depths: dict[str, list[list[int]]] = {"4": [], "5": []}
    for row in [*development, *validation, *final_test]:
        result = plan_story(StorySpec.from_dict(row))
        if result.certificate.status is not StoryStatus.PLAN_FEASIBLE:
            feasible_failures.append(
                {
                    "sample_id": row["sample_id"],
                    "status": str(result.certificate.status),
                    "reason_codes": result.certificate.reason_codes,
                }
            )
        else:
            first = next(iter(result.certificate.selected_depths.values()))
            if first not in observed_depths[str(row["depth"])]:
                observed_depths[str(row["depth"])].append(first)

    sentinel_failures: list[dict[str, Any]] = []
    sentinel_reason_counts: dict[str, int] = {}
    for row in sentinels:
        result = plan_story(StorySpec.from_dict(row))
        reasons = list(result.certificate.reason_codes)
        for reason in reasons:
            sentinel_reason_counts[reason] = sentinel_reason_counts.get(reason, 0) + 1
        if (
            result.certificate.status is not StoryStatus.PLAN_INFEASIBLE
            or row["expected_reason_code"] not in reasons
        ):
            sentinel_failures.append(
                {
                    "sample_id": row["sample_id"],
                    "status": str(result.certificate.status),
                    "reason_codes": reasons,
                    "expected_reason_code": row["expected_reason_code"],
                }
            )

    if feasible_failures or sentinel_failures:
        raise RuntimeError(
            json.dumps(
                {
                    "feasible_failures": feasible_failures,
                    "sentinel_failures": sentinel_failures,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return {
        "development_plan_feasible": len(development),
        "validation_plan_feasible": len(validation),
        "final_test_plan_feasible": len(final_test),
        "sentinel_plan_infeasible": len(sentinels),
        "sentinel_reason_counts": sentinel_reason_counts,
        "selected_depth_patterns": observed_depths,
    }


def build(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    development = build_pretest_specs("development", 32, 1)
    validation = build_pretest_specs("validation", 16, 2)
    final_test = build_final_test_specs()
    sentinels = build_sentinel_specs()
    verification = _verify(development, validation, final_test, sentinels)

    _write_jsonl(output_dir / "development_specs.jsonl", development)
    _write_jsonl(output_dir / "validation_specs.jsonl", validation)
    _write_jsonl(output_dir / "final_test_specs.jsonl", final_test)
    _write_jsonl(output_dir / "sentinel_specs.jsonl", sentinels)
    _write_json(output_dir / "lexical_unit_bank.json", LEXICAL_BANK)

    scenario_by_stratum: dict[str, dict[str, int]] = {}
    for row in final_test:
        counts = scenario_by_stratum.setdefault(row["stratum"], {})
        counts[row["scenario_type"]] = counts.get(row["scenario_type"], 0) + 1
    config = {
        "generator_version": GENERATOR_VERSION,
        "global_seed": GLOBAL_SEED,
        "design": {
            "cefr_levels": ["A1", "B1", "B2"],
            "target_counts": [4, 8],
            "terminal_path_counts": [8, 16],
            "final_test_per_stratum": 20,
            "sentinels_per_stratum": 2,
            "scenario_counts_per_stratum": SCENARIO_COUNTS,
        },
        "counts": {
            "development": len(development),
            "validation": len(validation),
            "final_test_feasible": len(final_test),
            "sentinel": len(sentinels),
            "formal_test_total": len(final_test) + len(sentinels),
        },
        "scenario_counts_verified": scenario_by_stratum,
        "planner_verification": verification,
        "target_defaults": {
            "min_occurrences": 3,
            "min_gap": 0,
            "max_gap": 1,
            "min_contexts": 2,
            "context_label_count": 3,
            "required_phases": ["opening", "middle", "ending"],
            "mode_requirements": {"exposure": 1, "judgment": 1, "retrieval": 1},
        },
    }
    _write_json(output_dir / "benchmark_config.json", config)
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description='Write the PathLex benchmark specification files.')
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory for benchmark specification and configuration files.",
    )
    args = parser.parse_args()
    config = build(args.output_dir.resolve())
    print(json.dumps(config["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
