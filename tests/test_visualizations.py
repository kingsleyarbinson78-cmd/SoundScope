import pytest

from visualizations import create_comparison_figure


def test_comparison_figure_shows_three_measures_for_each_location() -> None:
	results = [
		{
			"location": "Library",
			"duration_seconds": 2.0,
			"rms_amplitude_fs": 0.1,
			"dominant_frequency_hz": 440.0,
		},
		{
			"location": "Canteen",
			"duration_seconds": 3.0,
			"rms_amplitude_fs": 0.3,
			"dominant_frequency_hz": None,
		},
	]

	figure = create_comparison_figure(results)

	assert len(figure.data) == 3
	assert list(figure.data[0].x) == ["Library", "Canteen"]
	assert list(figure.data[0].y) == [2.0, 3.0]
	assert list(figure.data[1].y) == [0.1, 0.3]
	assert list(figure.data[2].y) == [440.0, None]


def test_comparison_figure_rejects_empty_results() -> None:
	with pytest.raises(ValueError, match="At least one result"):
		create_comparison_figure([])