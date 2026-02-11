from bal_tools.ecosystem import StakeDAO


def test_calculate_dynamic_min_incentive():
    sd = StakeDAO()
    result = sd.calculate_dynamic_min_incentive()

    assert isinstance(result, int)
    assert result > 0
