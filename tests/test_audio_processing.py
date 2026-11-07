import csv
from io import BytesIO
from io import StringIO

import numpy as np
import pytest
import soundfile as sf

from audio_processing import (
	analyze_frequency_spectrum,
	calculate_audio_statistics,
	calculate_short_time_rms,
	detect_noise_events,
	generate_sample_audio,
	load_audio,
	results_to_csv,
)


def make_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
	buffer = BytesIO()
	sf.write(buffer, samples, sample_rate, format="WAV")
	return buffer.getvalue()


def test_load_audio_reads_mono_wav_as_two_dimensional_samples() -> None:
	original = np.array([0.0, 0.25, -0.5, 0.75], dtype=np.float32)

	samples, sample_rate = load_audio(make_wav_bytes(original, 16_000))

	assert sample_rate == 16_000
	assert samples.shape == (4, 1)
	assert samples.dtype == np.float32
	assert np.allclose(samples[:, 0], original, atol=1e-4)


def test_load_audio_preserves_stereo_channels() -> None:
	original = np.array([[0.1, -0.1], [0.2, -0.2]], dtype=np.float32)

	samples, sample_rate = load_audio(make_wav_bytes(original, 48_000))

	assert sample_rate == 48_000
	assert samples.shape == (2, 2)
	assert np.allclose(samples, original, atol=1e-4)


@pytest.mark.parametrize("audio_bytes", [b"", b"not an audio file"])
def test_load_audio_rejects_empty_or_invalid_data(audio_bytes: bytes) -> None:
	with pytest.raises(ValueError):
		load_audio(audio_bytes)


def test_generate_sample_audio_returns_expected_mono_tone() -> None:
	samples, sample_rate = generate_sample_audio(
		duration_seconds=1.0,
		sample_rate=8_000,
		frequency_hz=440.0,
	)

	assert samples.shape == (8_000, 1)
	assert sample_rate == 8_000
	assert samples.dtype == np.float32
	assert np.max(np.abs(samples)) == pytest.approx(0.6, abs=1e-5)


def test_generate_sample_audio_rejects_frequency_at_nyquist() -> None:
	with pytest.raises(ValueError, match="Nyquist"):
		generate_sample_audio(sample_rate=8_000, frequency_hz=4_000.0)


def test_frequency_spectrum_finds_generated_tone() -> None:
	samples, sample_rate = generate_sample_audio(
		duration_seconds=1.0,
		sample_rate=8_000,
		frequency_hz=440.0,
	)

	frequencies, magnitudes, dominant_frequency = analyze_frequency_spectrum(
		samples, sample_rate
	)

	assert frequencies.shape == magnitudes.shape
	assert dominant_frequency == pytest.approx(440.0, abs=1.0)
	assert np.max(magnitudes) == pytest.approx(0.6, abs=0.01)


def test_frequency_spectrum_returns_no_peak_for_silence() -> None:
	frequencies, magnitudes, dominant_frequency = analyze_frequency_spectrum(
		np.zeros((128, 1), dtype=np.float32), 8_000
	)

	assert frequencies.size > 0
	assert np.all(magnitudes == 0)
	assert dominant_frequency is None


def test_frequency_spectrum_handles_one_sample_recording() -> None:
	frequencies, magnitudes, dominant_frequency = analyze_frequency_spectrum(
		np.array([[0.5]], dtype=np.float32), 8_000
	)

	assert frequencies.size == 0
	assert magnitudes.size == 0
	assert dominant_frequency is None


def test_frequency_spectrum_does_not_cancel_opposite_phase_channels() -> None:
	mono, sample_rate = generate_sample_audio(
		duration_seconds=1.0,
		sample_rate=8_000,
		frequency_hz=440.0,
	)
	stereo = np.column_stack((mono[:, 0], -mono[:, 0]))

	_, _, dominant_frequency = analyze_frequency_spectrum(stereo, sample_rate)

	assert dominant_frequency == pytest.approx(440.0, abs=1.0)


def test_audio_statistics_calculate_amplitudes_and_crest_factor() -> None:
	samples = np.array([[3.0], [4.0]], dtype=np.float32)

	statistics = calculate_audio_statistics(samples, sample_rate=2)

	assert statistics["duration_seconds"] == 1.0
	assert statistics["rms_amplitude"] == pytest.approx(np.sqrt(12.5))
	assert statistics["peak_amplitude"] == 4.0
	assert statistics["crest_factor"] == pytest.approx(4.0 / np.sqrt(12.5))
	assert statistics["channel_count"] == 1


def test_audio_statistics_report_undefined_crest_factor_for_silence() -> None:
	statistics = calculate_audio_statistics(np.zeros((10, 1)), sample_rate=10)

	assert statistics["rms_amplitude"] == 0
	assert statistics["peak_amplitude"] == 0
	assert statistics["crest_factor"] is None


def test_short_time_rms_calculates_expected_non_overlapping_frames() -> None:
	samples = np.array([[1.0], [1.0], [0.0], [0.0]], dtype=np.float32)

	times, rms_values = calculate_short_time_rms(
		samples, sample_rate=1_000, frame_ms=2, hop_ms=2
	)

	assert np.allclose(times, [0.0, 0.002])
	assert np.allclose(rms_values, [1.0, 0.0])


def test_noise_event_detection_finds_a_loud_burst() -> None:
	samples = np.zeros((1_000, 1), dtype=np.float32)
	samples[200:400, 0] = 0.5

	events = detect_noise_events(
		samples,
		sample_rate=1_000,
		threshold_ratio=0.3,
		frame_ms=100,
		hop_ms=50,
	)

	assert len(events) == 1
	assert events[0]["start_seconds"] <= 0.2
	assert events[0]["end_seconds"] >= 0.4
	assert events[0]["peak_frame_rms"] == pytest.approx(0.5)


def test_noise_event_detection_does_not_report_silence() -> None:
	events = detect_noise_events(np.zeros((1_000, 1)), sample_rate=1_000)

	assert events == []


@pytest.mark.parametrize("threshold", [0, -0.1, 1.1, float("nan")])
def test_noise_event_detection_rejects_invalid_threshold(threshold: float) -> None:
	with pytest.raises(ValueError, match="Threshold"):
		detect_noise_events(np.ones((100, 1)), sample_rate=1_000, threshold_ratio=threshold)


def test_results_to_csv_writes_headers_and_escapes_values() -> None:
	results = [
		{"location": "Library, east wing", "duration_seconds": 2.5},
		{"location": "Canteen", "duration_seconds": 4.0},
	]

	csv_text = results_to_csv(results)
	parsed_rows = list(csv.DictReader(StringIO(csv_text)))

	assert parsed_rows == [
		{"location": "Library, east wing", "duration_seconds": "2.5"},
		{"location": "Canteen", "duration_seconds": "4.0"},
	]


def test_results_to_csv_rejects_empty_results() -> None:
	with pytest.raises(ValueError, match="At least one"):
		results_to_csv([])
