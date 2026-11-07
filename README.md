# SoundScope

SoundScope is a small Engineering Physics project for exploring recorded sound with Python. It plots an audio waveform, estimates its frequency content with an FFT, calculates digital-amplitude statistics, demonstrates a simple energy-threshold event detector, and compares recordings labelled by campus location.

The app is intended for learning and demonstration. It is not a certified noise meter and does not measure sound pressure level (dB SPL).

## Features

- Generate a two-second 440 Hz sample tone or upload WAV audio.
- View mono or stereo waveforms with zoom and pan controls.
- View a single-sided FFT magnitude spectrum and its strongest non-zero frequency bin.
- Calculate RMS amplitude, peak amplitude, crest factor, and duration.
- Detect candidate events with short-time RMS and an adjustable relative threshold.
- Compare multiple WAV files by location and download analysis or comparison CSV files.
- Read short explanations of the sound physics used in the analysis.

## Requirements

- macOS, Windows, or Linux
- Python 3.10 or newer
- No microphone, sensor, paid service, or network API is required

WAV is the enabled upload format. SoundFile can read additional formats in some environments, but the interface intentionally starts with WAV for predictable support.

## Install and Run on macOS

Open Terminal, change to the project folder, and create a virtual environment. A virtual environment keeps this project's packages separate from the system Python installation.

```zsh
cd /Users/sheebasharon/SoundScope
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local address printed by Streamlit, usually `http://localhost:8501`. Keep the terminal running while you use the app. Press `Ctrl+C` in that terminal to stop it. To use the app again later, activate the environment and rerun Streamlit:

```zsh
cd /Users/sheebasharon/SoundScope
source .venv/bin/activate
python -m streamlit run app.py
```

Run the automated tests from the project folder with the environment activated:

```zsh
python -m pytest -q
```

## How to Use the App

### Analyze one recording

1. In the sidebar, choose **Generated demo tone** to try the app without a file, or choose **Upload a WAV file**.
2. Inspect duration, sample rate, channel count, and the time-domain waveform. Use the Plotly toolbar to zoom or pan.
3. Read the RMS, peak, crest factor, and dominant-frequency results.
4. Adjust the sidebar event threshold to change which high-energy intervals are marked as candidate events.
5. Use **Download this analysis as CSV** to export the current recording's results.

### Compare campus locations

1. Use the sidebar's **Campus comparison** link to jump to the comparison section.
2. Upload at least two WAV files.
3. Give each recording a location label. The filename is used as the starting label, and it can be edited.
4. Compare duration, RMS amplitude, and dominant frequency in the table and plots.
5. Use **Download comparison as CSV** to export the comparison rows.

For meaningful field comparisons, record at similar distances and orientations with the same device and gain where possible. Different microphones, automatic gain control, background conditions, and positions can change digital amplitudes.

## Project Files

| File                             | Purpose                                                                                 |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| `app.py`                         | Streamlit interface, upload controls, results, and downloads                            |
| `audio_processing.py`            | WAV loading, sample generation, FFT, statistics, event detection, and CSV serialization |
| `visualizations.py`              | Interactive Plotly waveform, spectrum, and comparison charts                            |
| `requirements.txt`               | Python package version ranges                                                           |
| `.streamlit/config.toml`         | Dark navy theme and cyan accent settings                                                |
| `tests/test_audio_processing.py` | Tests for audio processing, event detection, and CSV output                             |
| `tests/test_visualizations.py`   | Tests for comparison charts                                                             |

## How the Calculations Work

### Audio samples and the waveform

A digital recording is a sequence of sample values. The code stores audio as an array with shape `(number of samples, number of channels)`. Mono audio has one channel; stereo has two. If the sampling rate is $f_s$ samples per second and the recording contains $N$ samples, its duration is:

$$T = \frac{N}{f_s}$$

The waveform plots sample amplitude against time. Its amplitude is a normalized digital value; it is not air pressure in pascals.

### Frequency and sampling

Frequency is the number of cycles per second, measured in hertz (Hz). For a repeating signal, $f = 1/T_p$, where $T_p$ is the period of one cycle. The sampling interval is $1/f_s$ seconds.

The Nyquist principle says that a sampled signal can represent frequencies only below half its sampling rate. For example, at 8,000 samples per second, the theoretical upper limit is 4,000 Hz. SoundScope's demo generator rejects a tone at or above that limit.

### FFT spectrum

The Fast Fourier Transform (FFT) represents a time signal as sinusoidal frequency components. SoundScope removes each channel's mean, applies a Hann window to reduce edge leakage, and calculates a single-sided magnitude spectrum. For $N$ samples, the frequency-bin spacing is:

$$\Delta f = \frac{f_s}{N}$$

Longer recordings generally give finer frequency spacing. The displayed dominant frequency is the largest non-zero spectrum bin; it is not necessarily the only frequency in a complex sound.

### RMS, peak, and crest factor

For sample values $x_1, x_2, \ldots, x_N$, RMS amplitude is:

$$x_{\mathrm{RMS}} = \sqrt{\frac{1}{N}\sum_{i=1}^{N}x_i^2}$$

Peak amplitude is the largest absolute sample. Crest factor is peak amplitude divided by RMS amplitude. RMS describes the overall digital signal level; crest factor describes how large the peaks are relative to that level. For silence, RMS is zero and crest factor is undefined.

### Candidate noise events

The detector calculates RMS over overlapping 50 ms frames with a 25 ms hop. It marks frames at or above the selected fraction of the largest frame RMS, groups nearby active frames, and reports their time intervals. The default threshold is 30%. This relative rule is useful for demonstrating energy changes, but it does not classify events as speech, music, or noise and is not a certified monitoring method.

## Measurement Limitations

Raw digital amplitude cannot be converted to accurate dB SPL without a calibrated microphone, known sensitivity, and controlled recording chain. The app therefore reports unitless digital full-scale amplitude (FS), not dB SPL. Even relative comparisons are affected by microphone response, gain, automatic processing, placement, room acoustics, and background conditions. Treat results as software-based comparisons, not regulatory measurements.

## Example Demo Results

The generated demo is a 440 Hz sine wave with amplitude 0.6, sampled at 44,100 Hz for two seconds. A typical run reports:

| Result                                    |         Example |
| ----------------------------------------- | --------------: |
| Duration                                  |         2.000 s |
| Sampling rate                             |       44,100 Hz |
| Channels                                  |               1 |
| RMS amplitude                             | about 0.4243 FS |
| Peak amplitude                            | about 0.6000 FS |
| Crest factor                              |      about 1.41 |
| Dominant frequency                        |        440.0 Hz |
| Candidate events at the default threshold |               1 |

Small numerical differences may occur from floating-point arithmetic. The event count describes the detector's threshold result, not a count of verified noise incidents.

## Suggested Experiments

1. **Amplitude and RMS:** generate tones at amplitudes 0.2, 0.4, and 0.8. Check whether RMS scales approximately in proportion to amplitude while frequency stays fixed.
2. **Frequency and pitch:** generate tones at 220, 440, and 880 Hz. Compare the configured tone frequency with the dominant-frequency result.
3. **Duration and FFT resolution:** compare one-second and two-second recordings at the same sample rate. Calculate $f_s/N$ and observe the change in frequency-bin spacing.
4. **Event threshold:** use a recording containing a quiet background and a short clap or tap. Change the threshold and observe how the detected interval changes. This is a demonstration, not calibrated loudness analysis.
5. **Campus comparison:** record several locations using the same device, gain, distance, and orientation. Compare RMS as a relative digital measure and discuss the remaining differences in the report.

## Four-Person Team Roles

- **Audio and physics:** explain sampling, Nyquist, FFT, and measurement limitations.
- **Processing and tests:** maintain WAV loading, calculations, and automated tests.
- **Interface and visualization:** maintain Streamlit controls and Plotly figures.
- **Experiment and reporting:** collect consistently recorded samples, interpret CSV results, and prepare the demonstration.

## Demonstration Checklist

- Start the app and show the generated 440 Hz tone.
- Point out duration, sample rate, channels, RMS, peak, crest factor, and dominant frequency.
- Zoom into the waveform and identify a repeating cycle.
- Explain why the frequency spectrum has a peak near 440 Hz.
- Adjust the event threshold and describe how the candidate event result changes.
- Upload two location-labelled WAV files and compare their rows and charts.
- Download a CSV and explain why its amplitude values are relative digital values, not dB SPL.

## Possible Viva Questions

**What is sound?**  
Sound is a mechanical longitudinal wave: particles in a medium oscillate approximately parallel to the direction the disturbance travels.

**What does sampling rate mean?**  
It is the number of audio samples stored each second, measured in samples per second or hertz.

**Why does the sampling rate matter?**  
It sets the time spacing between samples and, through the Nyquist principle, the highest frequency that can be represented without aliasing.

**What does the FFT show?**  
It estimates the strengths of frequency components present in a finite digital recording.

**Why use RMS instead of only peak amplitude?**  
Peak captures one largest sample, while RMS summarizes amplitude over all samples and is less dependent on a single peak.

**Can this app report dB SPL?**  
No. That needs a calibrated microphone and known reference. This app reports uncalibrated digital amplitudes.

**Why might two locations have different RMS values even if they seem equally loud?**  
Microphone response, gain, automatic processing, position, distance, orientation, and room acoustics can all change the recording.

**What does one detected event mean?**  
It means a group of short-time RMS frames crossed the configured relative threshold. It does not prove that a distinct noise incident occurred.

## Common Problems

- **`ModuleNotFoundError` for Streamlit or another package:** activate `.venv` and run `python -m pip install -r requirements.txt` from the project folder.
- **`streamlit: command not found`:** use `python -m streamlit run app.py` after activating `.venv`.
- **Port 8501 is already in use:** stop the other Streamlit process with `Ctrl+C`, or start this app on another port with `python -m streamlit run app.py --server.port 8502`.
- **The uploaded file is rejected:** use a non-empty, valid WAV file. This version only enables WAV uploads in the interface.
- **No dominant frequency is reported:** the recording may be silent or too short to contain a non-zero frequency bin.
- **The browser shows a stale import error after code edits:** stop the running Streamlit process with `Ctrl+C`, then run `python -m streamlit run app.py` again.
