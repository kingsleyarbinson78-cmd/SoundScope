import csv
from io import BytesIO
from io import StringIO

import numpy as np
import soundfile as sf


def load_audio(audio_bytes: bytes) -> tuple[np.ndarray, int]:
	"""Decode an audio file into normalized samples and its sampling rate."""
	if not audio_bytes:
		raise ValueError("The uploaded file is empty.")

	try:
		samples, sample_rate = sf.read(
			BytesIO(audio_bytes), dtype="float32", always_2d=True
		)
	except (RuntimeError, OSError, ValueError) as error:
		raise ValueError(
			"This file could not be decoded. Please upload a valid WAV recording."
		) from error

	if samples.shape[0] == 0:
		raise ValueError("The audio file contains no samples.")
	if sample_rate <= 0:
		raise ValueError("The audio file has an invalid sampling rate.")
	if not np.isfinite(samples).all():
		raise ValueError("The audio file contains invalid sample values.")

	return samples, sample_rate


def generate_sample_audio(
	duration_seconds: float = 2.0,
	sample_rate: int = 44_100,
	frequency_hz: float = 440.0,
	amplitude: float = 0.6,
) -> tuple[np.ndarray, int]:
	"""Create a mono sine wave for trying the app without a recording."""
	if not np.isfinite(duration_seconds) or duration_seconds <= 0:
		raise ValueError("Duration must be a positive, finite number of seconds.")
	if sample_rate <= 0:
		raise ValueError("Sampling rate must be a positive number of hertz.")
	if not np.isfinite(frequency_hz) or not 0 < frequency_hz < sample_rate / 2:
		raise ValueError("Frequency must be positive and below the Nyquist frequency.")
	if not np.isfinite(amplitude) or not 0 <= amplitude <= 1:
		raise ValueError("Amplitude must be between 0 and 1.")

	sample_count = max(1, round(duration_seconds * sample_rate))
	time_seconds = np.arange(sample_count, dtype=np.float32) / sample_rate
	samples = amplitude * np.sin(2 * np.pi * frequency_hz * time_seconds)
	return samples.astype(np.float32)[:, np.newaxis], sample_rate


def analyze_frequency_spectrum(
	samples: np.ndarray,
	sample_rate: int,
) -> tuple[np.ndarray, np.ndarray, float | None]:
	"""Return positive FFT frequencies, average channel magnitudes, and the peak."""
	if samples.ndim != 2 or samples.shape[0] == 0 or samples.shape[1] == 0:
		raise ValueError("Samples must have shape (frames, channels) and not be empty.")
	if sample_rate <= 0:
		raise ValueError("Sampling rate must be a positive number of hertz.")
	if not np.isfinite(samples).all():
		raise ValueError("Samples must contain only finite values.")

	sample_count = samples.shape[0]
	window = np.hanning(sample_count) if sample_count >= 3 else np.ones(sample_count)
	window_sum = float(np.sum(window))
	centered = samples.astype(np.float64) - np.mean(samples, axis=0)
	channel_spectra = np.fft.rfft(centered * window[:, np.newaxis], axis=0)
	magnitudes = np.abs(channel_spectra) / window_sum

	if sample_count % 2 == 0:
		magnitudes[1:-1] *= 2
	else:
		magnitudes[1:] *= 2

	frequencies = np.fft.rfftfreq(sample_count, d=1 / sample_rate)
	frequencies = frequencies[1:]
	average_magnitudes = np.mean(magnitudes[1:], axis=1)
	if average_magnitudes.size == 0 or not np.any(average_magnitudes > 0):
		return frequencies, average_magnitudes, None

	dominant_index = int(np.argmax(average_magnitudes))
	dominant_frequency = float(frequencies[dominant_index])
	return frequencies, average_magnitudes, dominant_frequency


def calculate_audio_statistics(
	samples: np.ndarray,
	sample_rate: int,
) -> dict[str, float | int | None]:
	"""Calculate whole-recording amplitude statistics in digital units."""
	if samples.ndim != 2 or samples.shape[0] == 0 or samples.shape[1] == 0:
		raise ValueError("Samples must have shape (frames, channels) and not be empty.")
	if sample_rate <= 0:
		raise ValueError("Sampling rate must be a positive number of hertz.")
	if not np.isfinite(samples).all():
		raise ValueError("Samples must contain only finite values.")

	peak_amplitude = float(np.max(np.abs(samples)))
	rms_amplitude = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
	crest_factor = peak_amplitude / rms_amplitude if rms_amplitude > 0 else None
	return {
		"duration_seconds": samples.shape[0] / sample_rate,
		"rms_amplitude": rms_amplitude,
		"peak_amplitude": peak_amplitude,
		"crest_factor": crest_factor,
		"channel_count": samples.shape[1],
	}


def calculate_short_time_rms(
	samples: np.ndarray,
	sample_rate: int,
	frame_ms: float = 50.0,
	hop_ms: float = 25.0,
) -> tuple[np.ndarray, np.ndarray]:
	"""Calculate RMS energy in overlapping frames, returning start times in seconds."""
	if samples.ndim != 2 or samples.shape[0] == 0 or samples.shape[1] == 0:
		raise ValueError("Samples must have shape (frames, channels) and not be empty.")
	if sample_rate <= 0:
		raise ValueError("Sampling rate must be a positive number of hertz.")
	if not np.isfinite(frame_ms) or frame_ms <= 0:
		raise ValueError("Frame length must be a positive, finite number of milliseconds.")
	if not np.isfinite(hop_ms) or hop_ms <= 0:
		raise ValueError("Frame hop must be a positive, finite number of milliseconds.")
	if not np.isfinite(samples).all():
		raise ValueError("Samples must contain only finite values.")

	frame_length = max(1, round(sample_rate * frame_ms / 1000))
	hop_length = max(1, round(sample_rate * hop_ms / 1000))
	starts = np.arange(0, samples.shape[0], hop_length)
	rms_values = np.empty(starts.size, dtype=np.float64)
	for frame_index, start in enumerate(starts):
		frame = samples[start : min(start + frame_length, samples.shape[0])]
		rms_values[frame_index] = np.sqrt(
			np.mean(np.square(frame, dtype=np.float64))
		)

	return starts / sample_rate, rms_values


def detect_noise_events(
	samples: np.ndarray,
	sample_rate: int,
	threshold_ratio: float = 0.3,
	frame_ms: float = 50.0,
	hop_ms: float = 25.0,
	min_event_ms: float = 50.0,
	merge_gap_ms: float = 100.0,
) -> list[dict[str, float]]:
	"""Find energetic intervals using a fraction of peak short-time RMS."""
	if not np.isfinite(threshold_ratio) or not 0 < threshold_ratio <= 1:
		raise ValueError("Threshold must be greater than 0 and no more than 1.")
	if not np.isfinite(min_event_ms) or min_event_ms <= 0:
		raise ValueError("Minimum event duration must be a positive number of milliseconds.")
	if not np.isfinite(merge_gap_ms) or merge_gap_ms < 0:
		raise ValueError("Merge gap must be a non-negative number of milliseconds.")

	frame_times, rms_values = calculate_short_time_rms(
		samples, sample_rate, frame_ms, hop_ms
	)
	if rms_values.size == 0 or not np.any(rms_values > 0):
		return []

	threshold = threshold_ratio * float(np.max(rms_values))
	active_frames = np.flatnonzero((rms_values >= threshold) & (rms_values > 0))
	if active_frames.size == 0:
		return []

	frame_length = max(1, round(sample_rate * frame_ms / 1000))
	hop_length = max(1, round(sample_rate * hop_ms / 1000))
	merge_gap_samples = round(sample_rate * merge_gap_ms / 1000)
	max_frame_gap = (frame_length + merge_gap_samples) // hop_length
	minimum_duration = min_event_ms / 1000
	events: list[dict[str, float]] = []
	group_start = int(active_frames[0])
	previous_frame = group_start

	def add_event(first_frame: int, last_frame: int) -> None:
		start_sample = int(round(frame_times[first_frame] * sample_rate))
		last_start_sample = int(round(frame_times[last_frame] * sample_rate))
		end_sample = min(samples.shape[0], last_start_sample + frame_length)
		start_time = start_sample / sample_rate
		end_time = end_sample / sample_rate
		if end_time - start_time >= minimum_duration:
			events.append(
				{
					"start_seconds": start_time,
					"end_seconds": end_time,
					"peak_frame_rms": float(np.max(rms_values[first_frame : last_frame + 1])),
				}
			)

	for frame_index_value in active_frames[1:]:
		frame_index = int(frame_index_value)
		if frame_index - previous_frame > max_frame_gap:
			add_event(group_start, previous_frame)
			group_start = frame_index
		previous_frame = frame_index
	add_event(group_start, previous_frame)
	return events


def results_to_csv(results: list[dict[str, object]]) -> str:
	"""Serialize result dictionaries as downloadable CSV text."""
	if not results:
		raise ValueError("At least one result row is required to create a CSV file.")

	fieldnames = list(dict.fromkeys(key for row in results for key in row))
	buffer = StringIO(newline="")
	writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
	writer.writeheader()
	writer.writerows(results)
	return buffer.getvalue()
