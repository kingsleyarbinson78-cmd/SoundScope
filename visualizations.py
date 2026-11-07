import math

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_waveform_figure(
	samples: np.ndarray,
	sample_rate: int,
	max_points: int = 12_000,
) -> go.Figure:
	"""Build an interactive time-domain plot for one or more channels."""
	if samples.ndim != 2 or samples.shape[0] == 0:
		raise ValueError("Waveform samples must have shape (frames, channels).")
	if sample_rate <= 0:
		raise ValueError("Sampling rate must be a positive number of hertz.")
	if max_points <= 0:
		raise ValueError("Maximum plot points must be positive.")

	step = max(1, math.ceil(samples.shape[0] / max_points))
	indices = np.arange(0, samples.shape[0], step)
	time_seconds = indices / sample_rate
	colors = ("#36c5d8", "#f3a65b", "#83d17a", "#d88ac5")

	figure = go.Figure()
	for channel_index in range(samples.shape[1]):
		figure.add_trace(
			go.Scatter(
				x=time_seconds,
				y=samples[indices, channel_index],
				mode="lines",
				name=f"Channel {channel_index + 1}",
				line={"color": colors[channel_index % len(colors)], "width": 0.8},
			)
		)

	figure.update_layout(
		template="plotly_dark",
		paper_bgcolor="rgba(0, 0, 0, 0)",
		plot_bgcolor="rgba(0, 0, 0, 0)",
		font={"color": "#e7eef4"},
		margin={"l": 20, "r": 20, "t": 20, "b": 20},
		height=360,
		legend={"orientation": "h", "y": 1.12},
		xaxis_title="Time (s)",
		yaxis_title="Digital amplitude (full scale, unitless)",
		hovermode="x unified",
	)
	return figure


def create_spectrum_figure(
	frequencies: np.ndarray,
	magnitudes: np.ndarray,
) -> go.Figure:
	"""Build a frequency-domain plot from a single-sided magnitude spectrum."""
	if frequencies.ndim != 1 or magnitudes.ndim != 1:
		raise ValueError("Spectrum frequencies and magnitudes must be one-dimensional.")
	if frequencies.shape != magnitudes.shape:
		raise ValueError("Spectrum frequencies and magnitudes must have equal lengths.")

	figure = go.Figure(
		data=[
			go.Scatter(
				x=frequencies,
				y=magnitudes,
				mode="lines",
				name="Magnitude spectrum",
				line={"color": "#36c5d8", "width": 1.5},
			)
		]
	)
	figure.update_layout(
		template="plotly_dark",
		paper_bgcolor="rgba(0, 0, 0, 0)",
		plot_bgcolor="rgba(0, 0, 0, 0)",
		font={"color": "#e7eef4"},
		margin={"l": 20, "r": 20, "t": 20, "b": 20},
		height=340,
		showlegend=False,
		xaxis_title="Frequency (Hz)",
		yaxis_title="Magnitude (digital full scale, unitless)",
		hovermode="x unified",
	)
	return figure


def create_comparison_figure(
	results: list[dict[str, object]],
) -> go.Figure:
	"""Compare duration, RMS amplitude, and dominant frequency by location."""
	if not results:
		raise ValueError("At least one result is required for a comparison chart.")

	locations = [str(result["location"]) for result in results]
	durations = [float(result["duration_seconds"]) for result in results]
	rms_amplitudes = [float(result["rms_amplitude_fs"]) for result in results]
	dominant_frequencies = [
		None
		if result["dominant_frequency_hz"] is None
		else float(result["dominant_frequency_hz"])
		for result in results
	]
	colors = ["#36c5d8", "#f3a65b", "#83d17a", "#d88ac5"]
	bar_colors = [colors[index % len(colors)] for index in range(len(results))]
	figure = make_subplots(
		rows=3,
		cols=1,
		shared_xaxes=True,
		subplot_titles=("Duration (s)", "RMS amplitude (FS, unitless)", "Dominant frequency (Hz)"),
		vertical_spacing=0.12,
	)
	for row_number, values in enumerate(
		(durations, rms_amplitudes, dominant_frequencies), start=1
	):
		figure.add_trace(
			go.Bar(x=locations, y=values, marker_color=bar_colors, showlegend=False),
			row=row_number,
			col=1,
		)

	figure.update_layout(
		template="plotly_dark",
		paper_bgcolor="rgba(0, 0, 0, 0)",
		plot_bgcolor="rgba(0, 0, 0, 0)",
		font={"color": "#e7eef4"},
		margin={"l": 30, "r": 20, "t": 50, "b": 30},
		height=760,
		bargap=0.35,
	)
	figure.update_xaxes(title_text="Location", row=3, col=1)
	return figure
