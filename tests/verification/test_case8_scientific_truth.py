"""Scientific golden assertions for the Case8 functional slice (Window 4 QA).

Every expected value is obtained from :mod:`tests.verification.case8_facts`, which
derives them from frozen evidence. No intermediate snapshot time is written as
``T/5``; the middle times are read from the canonical schedule and asserted to be
*not* equal to the naive equal-spacing value.
"""

from __future__ import annotations

import pytest

from tests.verification.case8_facts import (CONFIG_COUNT, CONFIGS,
                                            HISTORY_ROWS_PER_CONFIG, FACTS,
                                            SNAPSHOT_COUNT_PER_CONFIG)


# ---------------------------------------------------------------------------
# Group A — the window-level expectations themselves
# ---------------------------------------------------------------------------

def test_config_identity_set_is_the_four_recorded_configurations():
    assert CONFIGS == ("A_u", "B_u", "C_u", "D_u")
    assert CONFIG_COUNT == 4


def test_window_level_aggregates_are_the_product_of_per_config_facts():
    assert FACTS.fact("window.snapshot_count_expected").value == 24
    assert FACTS.fact("window.snapshot_count_expected").value == CONFIG_COUNT * SNAPSHOT_COUNT_PER_CONFIG
    assert FACTS.fact("window.history_rows_expected").value == 7648
    assert FACTS.fact("window.history_rows_expected").value == CONFIG_COUNT * HISTORY_ROWS_PER_CONFIG


@pytest.mark.parametrize("config_id", CONFIGS)
def test_each_config_has_six_recorded_snapshots(config_id):
    fact = FACTS.fact(f"snapshots.{config_id}")
    assert fact.confidence == "L1"
    assert fact.value == SNAPSHOT_COUNT_PER_CONFIG == 6
    assert FACTS.fact("window.snapshot_count_expected").value == 24


@pytest.mark.parametrize("config_id", CONFIGS)
def test_each_config_has_1912_accepted_step_history_records(config_id):
    config = next(item for item in FACTS.configs if item.config_id == config_id)
    assert config.history_rows == HISTORY_ROWS_PER_CONFIG == 1912
    assert FACTS.fact("window.history_rows_expected").value == 7648


def test_accepted_step_expectation_matches_recorded_history_row_count():
    assert FACTS.fact("history.crosscheck").value is True
    assert FACTS.fact("accepted_steps").value == HISTORY_ROWS_PER_CONFIG


# ---------------------------------------------------------------------------
# Group B — the D_u terminal snapshot identity
# ---------------------------------------------------------------------------

def test_du_final_snapshot_index_step_and_time():
    config = next(item for item in FACTS.configs if item.config_id == "D_u")
    final = config.snapshots[-1]
    assert final.index == 6
    assert final.step_index == 1912
    assert final.physical_time == 0.08
    assert FACTS.fact("final_time").value == 0.08


@pytest.mark.parametrize("config_id", CONFIGS)
def test_terminal_snapshot_is_index_six_for_every_configuration(config_id):
    config = next(item for item in FACTS.configs if item.config_id == config_id)
    assert config.snapshots[-1].index == 6
    assert config.snapshots[-1].step_index == 1912
    assert config.snapshots[-1].physical_time == 0.08


# ---------------------------------------------------------------------------
# Group C — snapshot numbering and the prohibition of a zero index
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("config_id", CONFIGS)
def test_snapshot_index_is_strictly_one_based_and_contiguous(config_id):
    config = next(item for item in FACTS.configs if item.config_id == config_id)
    indices = [item.index for item in config.snapshots]
    assert indices == [1, 2, 3, 4, 5, 6]
    assert 0 not in indices, "SNAPSHOT_ZERO_ALLOWED must be NO"


def test_snapshot_index_zero_is_not_a_legal_alias_for_the_initial_frame():
    """snapshot_index=0 is INVALID; the initial frame is snapshot_index=1, step_index=0."""
    for config in FACTS.configs:
        initial = config.snapshots[0]
        assert initial.index == 1
        assert initial.step_index == 0
        assert all(item.index != 0 for item in config.snapshots)


# ---------------------------------------------------------------------------
# Group D — intermediate snapshot times must not be T/5
# ---------------------------------------------------------------------------

def test_intermediate_snapshot_times_are_not_naive_equal_spacing():
    times = [item.physical_time for item in FACTS.configs[0].snapshots]
    final_time = FACTS.fact("final_time").value
    naive = [final_time * step / 5 for step in range(6)]
    deviations = [abs(actual - guess) for actual, guess in zip(times[1:5], naive[1:5])]
    assert all(deviation > 1e-6 for deviation in deviations), (
        "recorded intermediate times must come from the canonical schedule, not T/5")


def test_snapshot_times_are_strictly_increasing_and_anchored_at_zero():
    times = [item.physical_time for item in FACTS.configs[0].snapshots]
    assert times[0] == 0.0
    assert times[-1] == FACTS.fact("final_time").value
    assert all(later > earlier for earlier, later in zip(times, times[1:]))


@pytest.mark.parametrize("config_id", CONFIGS)
def test_snapshot_schedule_is_identical_across_configurations(config_id):
    lock_times = FACTS.fact("snapshot_times").value
    lock_steps = FACTS.fact("snapshot_steps").value
    config = next(item for item in FACTS.configs if item.config_id == config_id)
    assert tuple(item.physical_time for item in config.snapshots) == lock_times
    assert tuple(item.step_index for item in config.snapshots) == lock_steps


# ---------------------------------------------------------------------------
# Group E — curve endpoints come from the recorded source
# ---------------------------------------------------------------------------

def test_cumulative_and_stage_increment_are_distinct_recorded_columns():
    assert FACTS.fact("D_u.E_at.rows_distinct").value is True
    assert FACTS.fact("D_u.E_at.first").value != FACTS.fact("D_u.E_at.terminal").value


def test_du_terminal_E_at_matches_the_recorded_source_value():
    assert FACTS.fact("D_u.E_at.terminal").value == 0.0027771079325925934
    assert FACTS.fact("D_u.E_at.terminal").confidence == "L2"
    assert FACTS.fact("D_u.E_at.terminal_source_time").value == 0.08


def test_recorded_history_asset_hash_is_available_for_drift_detection():
    digest = FACTS.fact("history.sha256.D_u").value
    assert len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)
