Audio Converter & Tagger

Audio Converter & Tagger is a high-performance desktop application built with Python for metadata management, audio format conversion, and technical integrity verification. Unlike standard editors, this tool uses Digital Signal Processing (DSP) to analyze the physical audio signal, identifying if a file's quality is legitimate or if it has been artificially upsampled (fake 320kbps).

🚀 Key Features

-   Multiformat Management: Read and write metadata for .mp3, .m4a (AAC/ALAC), .flac, and .wav files.
-   Integrated Converter: Batch convert lossless files (FLAC/WAV) to high-quality MP3 (320kbps) while preserving original tags.
-   Spectral Verification (FFT): Real-time analysis of the audio signal to identify the frequency "cutoff" point.
-   Cover Art Editor: Manage album artwork (ID3v2 APIC frames and MP4 covr atoms) with a built-in preview.
-   Modern UI: A clean, dark-themed interface built with CustomTkinter featuring native Drag & Drop support.

🛠️ Tech Stack

-   Language: Python 3.10+
-   GUI Framework: CustomTkinter & TkinterDnD2
-   Audio Engine: FFmpeg (via Subprocess)
-   Signal Analysis: Numpy & Scipy (Fast Fourier Transform)
-   Metadata Management: Mutagen

📐 Technical Logic: Detecting "Fake" Quality
The application bypasses unreliable metadata headers and analyzes the raw PCM data through a specific engineering pipeline:

-   PCM Sampling: The engine extracts a 5-second raw segment from the track's midpoint using FFmpeg pipes.
-   Fourier Transform: It applies a Fast Fourier Transform (FFT) to translate the signal from the time domain to the frequency domain.
-   Cutoff Analysis: The algorithm identifies the frequency threshold where energy magnitude drops below -60dB.

Diagnosis:

-   > 18.5 kHz: Genuine high-quality (320kbps or Lossless).
-   16.0 kHz - 17.0 kHz: Mid-range quality (Real ~192-256kbps).
-   < 16.0 kHz: Low quality / Upsampled (Fake 320kbps).

📥 Installation

1. Clone the repository

    git clone https://github.com/Sarapa17/Audio-Converter-Tagger-Pro.git
    cd Audio-Converter-Tagger-Pro

2. Install dependencies

    pip install -r requirements.txt

3. Setup FFmpeg
   The application requires FFmpeg.
   macOS: brew install ffmpeg
   Windows: Download the binary from ffmpeg.org and add it to your System PATH or project root.
