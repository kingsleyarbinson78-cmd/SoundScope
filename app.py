from pathlib import Path

import streamlit as st

from audio_processing import (
	analyze_frequency_spectrum,
	calculate_audio_statistics,
	detect_noise_events,
	generate_sample_audio,
	load_audio,
	results_to_csv,
)
from visualizations import (
	create_comparison_figure,
	create_spectrum_figure,
	create_waveform_figure,
)


st.set_page_config(
	page_title="SoundScope | Sound Wave Analysis",
	page_icon="🔊",
	layout="wide",
)

st.markdown(
	"""
	<style>
	:root {
		--soundscope-background: #101923;
		--soundscope-sidebar: #172632;
		--soundscope-surface: #1b2b37;
		--soundscope-border: #304651;
		--soundscope-text: #e7eef4;
		--soundscope-muted: #a9bdc7;
		--soundscope-accent: #36c5d8;
	}
	.stApp {
		background: var(--soundscope-background);
		color: var(--soundscope-text);
	}
	[data-testid="stAppViewContainer"] {
		background: var(--soundscope-background);
	}
	[data-testid="stHeader"] {
		background: var(--soundscope-background);
	}
	[data-testid="stSidebar"] {
		background: var(--soundscope-sidebar);
		border-right: 1px solid var(--soundscope-border);
	}
	[data-testid="stSidebar"] * {
		color: var(--soundscope-text);
	}
	[data-testid="stSidebar"] a {
		color: var(--soundscope-accent) !important;
	}
	[data-testid="stMarkdownContainer"] p {
		line-height: 1.55;
	}
	[data-testid="stMetric"] {
		background: var(--soundscope-surface);
		border: 1px solid var(--soundscope-border);
		padding: 1rem;
		border-radius: 6px;
	}
	[data-testid="stMetricLabel"] {
		color: var(--soundscope-muted);
	}
	[data-testid="stMetricValue"] {
		font-size: 1.55rem;
		line-height: 1.25;
	}
	[data-testid="stCaptionContainer"] p {
		color: var(--soundscope-muted);
	}
	[data-testid="stDataFrame"] {
		border: 1px solid var(--soundscope-border);
		border-radius: 6px;
	}
	[data-testid="stDownloadButton"] button {
		background: var(--soundscope-accent);
		border: 0;
		color: #0c1920;
		font-weight: 650;
	}
	h1, h2, h3 {
		color: var(--soundscope-text);
		font-family: "Avenir Next", "Trebuchet MS", sans-serif;
	}
	h1 {
		font-size: 2.2rem;
	}
	h2 {
		font-size: 1.5rem;
	}
	h3 {
		font-size: 1.2rem;
	}
	</style>
	""",
	unsafe_allow_html=True,
)

st.sidebar.title("SoundScope")
st.sidebar.caption("Engineering Physics project")
st.sidebar.markdown("### Navigate")
st.sidebar.markdown(
	"[01 | Recording analysis](#recording-analysis)  \n"
	"[02 | Campus comparison](#campus-comparison)  \n"
	"[03 | Physics guide](#physics-guide)"
)
st.sidebar.divider()
st.sidebar.header("Audio input")
audio_source = st.sidebar.radio(
	"Choose a source",
	("Generated demo tone", "Upload a WAV file"),
)
event_threshold_percent = st.sidebar.slider(
	"Event threshold (% of peak frame RMS)",
	min_value=5,
	max_value=95,
	value=30,
	step=5,
)

st.title("SoundScope")
st.subheader("Software-based sound wave analysis")
st.write(
	"Explore the shape and frequency content of recordings, and compare "
	"sound across campus locations."
)

current_analysis_row = None
st.markdown('<div id="recording-analysis"></div>', unsafe_allow_html=True)
st.markdown("### Audio waveform")
samples = None
sample_rate = None
filename = None

if audio_source == "Generated demo tone":
	samples, sample_rate = generate_sample_audio()
	filename = "Generated 440 Hz demo tone"
else:
	uploaded_file = st.file_uploader(
		"Upload a WAV recording",
		type=["wav"],
		help="WAV is enabled for this first version. Maximum upload size is set by Streamlit.",
	)
	if uploaded_file is not None:
		filename = uploaded_file.name
		try:
			with st.spinner("Reading audio file..."):
				samples, sample_rate = load_audio(uploaded_file.getvalue())
		except ValueError as error:
			st.error(str(error))
	else:
		st.info("Choose a WAV recording to begin, or select the generated demo tone.")

if samples is not None and sample_rate is not None:
	duration_seconds = samples.shape[0] / sample_rate
	channel_count = samples.shape[1]
	st.caption(f"Selected audio: {filename}")
	metric_columns = st.columns(3)
	metric_columns[0].metric("Duration", f"{duration_seconds:.3f} s")
	sampling_rate_label = (
		f"{sample_rate / 1000:g} kHz" if sample_rate >= 1_000 else f"{sample_rate} Hz"
	)
	metric_columns[1].metric("Sampling rate", sampling_rate_label)
	metric_columns[2].metric("Channels", str(channel_count))

	st.plotly_chart(
		create_waveform_figure(samples, sample_rate),
		width="stretch",
	)
	st.caption(
		"Amplitude is shown in digital full-scale units, not calibrated sound pressure. "
		"Use the chart toolbar to zoom and inspect a time interval."
	)

	st.markdown("### Sound statistics")
	statistics = calculate_audio_statistics(samples, sample_rate)
	crest_factor = statistics["crest_factor"]
	stat_columns = st.columns(3)
	stat_columns[0].metric(
		"RMS amplitude",
		f"{statistics['rms_amplitude']:.4f}",
		help="Root-mean-square digital amplitude over the recording; unitless and not dB SPL.",
	)
	stat_columns[1].metric(
		"Peak amplitude",
		f"{statistics['peak_amplitude']:.4f}",
		help="Largest absolute digital sample; full scale is 1.0.",
	)
	stat_columns[2].metric(
		"Crest factor",
		"N/A" if crest_factor is None else f"{crest_factor:.2f}",
		help="Peak amplitude divided by RMS amplitude. It is undefined for silence.",
	)
	st.caption(
		"RMS summarizes the signal's average digital amplitude; peak is its largest sample. "
		"Neither gives calibrated sound pressure without microphone calibration."
	)

	st.markdown("### Frequency spectrum")
	frequencies, magnitudes, dominant_frequency = analyze_frequency_spectrum(
		samples, sample_rate
	)
	if dominant_frequency is None:
		st.metric("Dominant frequency", "Not detected")
		st.info("No non-zero frequency component was found. The recording may be silent or too short.")
	else:
		st.metric("Dominant frequency", f"{dominant_frequency:.1f} Hz")
	st.plotly_chart(
		create_spectrum_figure(frequencies, magnitudes),
		width="stretch",
	)
	st.caption(
		"Magnitude is a relative digital amplitude. It is not a calibrated sound-pressure level."
	)

	st.markdown("### Noise-event detection")
	events = detect_noise_events(
		samples,
		sample_rate,
		threshold_ratio=event_threshold_percent / 100,
	)
	st.metric("Candidate events", len(events))
	if events:
		event_rows = [
			{
				"Start (s)": round(event["start_seconds"], 3),
				"End (s)": round(event["end_seconds"], 3),
				"Peak frame RMS (FS, unitless)": round(event["peak_frame_rms"], 4),
			}
			for event in events
		]
		st.dataframe(event_rows, hide_index=True, width="stretch")
	else:
		st.caption("No candidate events found at this threshold.")
	st.caption(
		"This basic detector flags short-time RMS frames above the selected fraction "
		"of the recording's loudest frame. It does not distinguish noise from speech "
		"or music and is not a certified noise-monitoring instrument."
	)
	current_analysis_row = {
		"filename": filename,
		"duration_seconds": statistics["duration_seconds"],
		"sampling_rate_hz": sample_rate,
		"channel_count": channel_count,
		"rms_amplitude_fs": statistics["rms_amplitude"],
		"peak_amplitude_fs": statistics["peak_amplitude"],
		"crest_factor": statistics["crest_factor"],
		"dominant_frequency_hz": dominant_frequency,
		"candidate_event_count": len(events),
	}
	st.download_button(
		"Download this analysis as CSV",
		data=results_to_csv([current_analysis_row]),
		file_name="soundscope_analysis.csv",
		mime="text/csv",
	)

st.markdown('<div id="campus-comparison"></div>', unsafe_allow_html=True)
st.divider()
st.markdown("### Campus recording comparison")
st.write(
	"Upload recordings from different locations and compare their duration, "
	"RMS amplitude, and dominant frequency."
)
comparison_uploads = st.file_uploader(
	"Upload WAV recordings to compare",
	type=["wav"],
	accept_multiple_files=True,
	key="comparison_uploads",
)
st.caption(
	"Enter a campus location or a custom label for each recording. For a fair "
	"comparison, note that microphones, gain settings, and recording conditions "
	"can change the measured digital amplitudes."
)

comparison_results = []
for upload_index, comparison_upload in enumerate(comparison_uploads):
	default_location = Path(comparison_upload.name).stem.replace("_", " ")
	location = st.text_input(
		f"Location for {comparison_upload.name}",
		value=default_location,
		placeholder="Classroom, Corridor, Canteen, Library, Outdoor area, or custom name",
		key=f"comparison_location_{upload_index}_{comparison_upload.name}",
	)
	try:
		comparison_samples, comparison_sample_rate = load_audio(
			comparison_upload.getvalue()
		)
		comparison_statistics = calculate_audio_statistics(
			comparison_samples, comparison_sample_rate
		)
		_, _, comparison_dominant_frequency = analyze_frequency_spectrum(
			comparison_samples, comparison_sample_rate
		)
		comparison_results.append(
			{
				"location": location.strip() or default_location,
				"filename": comparison_upload.name,
				"duration_seconds": comparison_statistics["duration_seconds"],
				"sampling_rate_hz": comparison_sample_rate,
				"channel_count": comparison_statistics["channel_count"],
				"rms_amplitude_fs": comparison_statistics["rms_amplitude"],
				"dominant_frequency_hz": comparison_dominant_frequency,
			}
		)
	except ValueError as error:
		st.error(f"Could not analyze {comparison_upload.name}: {error}")

if len(comparison_results) >= 2:
	comparison_table = [
		{
			"Location": result["location"],
			"File": result["filename"],
			"Duration (s)": round(result["duration_seconds"], 3),
			"RMS amplitude (FS, unitless)": round(result["rms_amplitude_fs"], 4),
			"Dominant frequency (Hz)": (
				None
				if result["dominant_frequency_hz"] is None
				else round(result["dominant_frequency_hz"], 1)
			),
		}
		for result in comparison_results
	]
	st.dataframe(comparison_table, hide_index=True, width="stretch")
	st.plotly_chart(create_comparison_figure(comparison_results), width="stretch")
	st.download_button(
		"Download comparison as CSV",
		data=results_to_csv(comparison_results),
		file_name="soundscope_comparison.csv",
		mime="text/csv",
	)
elif comparison_results:
	st.info("Upload at least one more valid WAV file to compare recordings.")
elif not comparison_uploads:
	st.info("Upload two or more WAV files to compare campus recordings.")

st.markdown('<div id="physics-guide"></div>', unsafe_allow_html=True)
st.markdown("### Physics guide")
with st.expander("The physics in brief"):
	st.write(
		"A waveform plots the microphone's digital samples against time. Its "
		"vertical position is the sample amplitude; the horizontal spacing is "
		"set by the sampling rate. A repeating waveform has a period, and its "
		"frequency is the number of cycles per second. Digital amplitude depends "
		"on the recording system and is not an absolute sound-pressure measurement."
	)

with st.expander("How the FFT finds frequencies"):
	st.write(
		"The Fast Fourier Transform (FFT) represents the recording as a sum of "
		"sinusoidal components. The spectrum shows the strength of each frequency "
		"in hertz; its largest non-zero component is reported as the dominant "
		"frequency. The frequency-bin spacing is the sampling rate divided by the "
		"number of samples, so short recordings have coarser frequency resolution."
	)

with st.expander("How RMS event detection works"):
	st.write(
		"The recording is split into overlapping short frames. For each frame, "
		"RMS is the square root of the mean of the squared sample amplitudes. "
		"Frames above the chosen fraction of the largest frame RMS are grouped "
		"into candidate events. The threshold is relative to this recording, not "
		"a calibrated sound-pressure level."
	)
