import sys
import os
import logging
from pathlib import Path
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip

# ----------------------------------------------------------------------
# Logging configuration
# ----------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
  
LOG_FILE = BASE_DIR / "add_sounds.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()          # also print to console
    ]
)
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
def add_sounds(filename: str) -> None:
    """
    Reads a timing file, overlays the specified sound clips onto
    ``output.mp4`` and writes the result to ``../final_video.mp4``.
    """
    log.info("Starting add_sounds() for file: %s", filename)

    # ------------------------------------------------------------------
    # Load the base video
    # ------------------------------------------------------------------
    video_path = BASE_DIR / "output.mp4"
    if not video_path.exists():
        log.error("Base video not found: %s", video_path)
        raise FileNotFoundError(f"Video file missing: {video_path}")

    log.info("Loading video: %s", video_path)
    video = VideoFileClip(str(video_path))
    duration = 0.0
    audio_clips = []

    # ------------------------------------------------------------------
    # Parse the timing file
    # ------------------------------------------------------------------
    timing_path = Path(filename)
    if not timing_path.exists():
        log.error("Timing file not found: %s", timing_path)
        raise FileNotFoundError(f"Timing file missing: {timing_path}")

    log.info("Reading timing file: %s", timing_path)
    with open(timing_path, encoding="utf8") as f:
        name_up_next = True
        for line_no, raw_line in enumerate(f.read().splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                log.debug("Line %d: empty – resetting name flag", line_no)
                name_up_next = True
                continue
            if line.startswith('#'):
                log.debug("Line %d: comment – skipping", line_no)
                continue

            # ----- WELCOME lines ------------------------------------------------
            if line.startswith("WELCOME"):
                parts = line.split('$^')
                if len(parts) < 2:
                    log.warning("Line %d: malformed WELCOME line – skipping", line_no)
                    continue

                if "#!" in line:
                    duration_part, sound_part = parts[1].split("#!")
                    sound_file = BASE_DIR / 'assets' / 'sounds' / 'mp3' / f'{sound_part.strip()}.mp3'
                    _add_audio_clip(sound_file, float(duration_part), audio_clips, duration)
                    duration += float(duration_part)
                    log.info(
                        "Line %d: WELCOME sound '%s' (%.2fs) at %.2fs",
                        line_no, sound_part.strip(), float(duration_part), duration
                    )
                else:
                    duration += float(parts[1])
                    log.info("Line %d: WELCOME pause %.2fs → new duration %.2fs", line_no, float(parts[1]), duration)
                continue

            # ----- Name lines ---------------------------------------------------
            if name_up_next:
                log.debug("Line %d: name line – will be used next", line_no)
                name_up_next = False
                continue

            # ----- Regular timed lines -----------------------------------------
            parts = line.split('$^')
            if len(parts) < 2:
                log.warning("Line %d: malformed timed line – skipping", line_no)
                continue

            if "#!" in line:
                duration_part, sound_part = parts[1].split("#!")
                sound_file = BASE_DIR / 'assets' / 'sounds' / 'mp3' / f'{sound_part.strip()}.mp3'
                _add_audio_clip(sound_file, float(duration_part), audio_clips, duration)
                duration += float(duration_part)
                log.info(
                    "Line %d: sound '%s' (%.2fs) at %.2fs",
                    line_no, sound_part.strip(), float(duration_part), duration
                )
            else:
                duration += float(parts[1])
                log.info("Line %d: pause %.2fs → new duration %.2fs", line_no, float(parts[1]), duration)

    # ------------------------------------------------------------------
    # Compose audio and write final video
    # ------------------------------------------------------------------
    if audio_clips:
        log.info("Compositing %d audio clip(s)", len(audio_clips))
        composite_audio = CompositeAudioClip(audio_clips)
        video = video.set_audio(composite_audio)
    else:
        log.warning("No audio clips were added – final video will keep original audio (or silence).")

    output_path = BASE_DIR.parent / "final_video.mp4"
    log.info("Writing final video to: %s", output_path)
    video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        verbose=False,      # moviepy already logs; we use our own logger
        logger=None
    )
    video.close()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    if video_path.exists():
        log.info("Removing temporary video: %s", video_path)
        os.remove(str(video_path))
    else:
        log.warning("Temporary video already gone: %s", video_path)

    log.info("add_sounds() finished successfully. Final video: %s", output_path)


# ----------------------------------------------------------------------
def _add_audio_clip(sound_file: Path, clip_duration: float, clip_list: list, start_time: float) -> None:
    """Helper that loads an audio file and appends it to the clip list."""
    if not sound_file.exists():
        log.error("Audio file missing: %s – skipping this clip", sound_file)
        return

    log.debug("Loading audio: %s (duration %.2fs) → start %.2fs", sound_file.name, clip_duration, start_time)
    audio_clip = AudioFileClip(str(sound_file)).set_start(start_time)
    clip_list.append(audio_clip)