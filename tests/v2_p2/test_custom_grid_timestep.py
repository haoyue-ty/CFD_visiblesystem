from types import SimpleNamespace
import copy

import numpy as np
import pytest

from backend.solver_runtime.worker import build_timestep, validate_recorded_request
from backend.services.v2.experiments import validate_experiment
from scripts.run_case8 import template_request


def test_short_custom_interval_keeps_six_distinct_source_checkpoints():
    setup = SimpleNamespace(mesh=SimpleNamespace(dx=.1, dy=.1),
                            state=np.array([[[1., 0., 0., 1.]]]), gas=None)
    config = SimpleNamespace(time=SimpleNamespace(cfl=.05, final_time=1e-8),
                             output=SimpleNamespace(checkpoint_fractions=(0., .2, .4, .6, .8, 1.)))
    result = build_timestep(setup, config, lambda state, gas: np.ones(state.shape[:-1]))
    assert result['steps'] >= 5
    assert len(result['checkpoint_steps']) == 6
    assert result['checkpoint_times'][0] == 0.
    assert result['checkpoint_times'][-1] == config.time.final_time
    assert result['dt'] <= result['raw_dt']


def test_legacy_availability_wording_can_change_without_changing_numerical_identity():
    request = template_request('case8.fast.D_u')
    request.submission.capability_revision = 'case8.capability.p2.1'
    saved = validate_experiment(request, allow_legacy=True).model_dump(mode='json')
    saved['warnings'][0] = 'Recorded historical availability notice'
    assert validate_recorded_request(request, saved).model_dump(mode='json') == saved
    tampered = copy.deepcopy(saved)
    tampered['normalized_config']['grid']['nx'] = 96
    with pytest.raises(RuntimeError, match='IDENTITY_MISMATCH'):
        validate_recorded_request(request, tampered)


def test_current_record_still_checks_warning_and_every_other_identity_field():
    request = template_request('case8.fast.D_u')
    saved = validate_experiment(request).model_dump(mode='json')
    saved['warnings'][0] = 'Changed current record'
    with pytest.raises(RuntimeError, match='IDENTITY_MISMATCH'):
        validate_recorded_request(request, saved)
