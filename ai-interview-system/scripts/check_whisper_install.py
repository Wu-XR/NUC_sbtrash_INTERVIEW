#!/usr/bin/env python3
# ...existing code...
import argparse
import os
import sys
import traceback


def check_imports():
    info = {}
    try:
        import whisper

        info["whisper_imported"] = True
        info["whisper_version"] = getattr(whisper, "__version__", "unknown")
    except Exception as e:  # pragma: no cover - best-effort check
        info["whisper_imported"] = False
        info["whisper_error"] = str(e)

    try:
        import torch

        info["torch_installed"] = True
        info["torch_version"] = getattr(torch, "__version__", "unknown")
        try:
            info["cuda_available"] = bool(torch.cuda.is_available())
        except Exception:
            info["cuda_available"] = False
    except Exception:
        info["torch_installed"] = False

    return info


def try_load_model(model_name: str, download: bool = True):
    import whisper

    if not download:
        # If user requested no download, avoid calling load_model which triggers downloads.
        return {"loaded": None, "note": "skipped (no-download)"}

    # Try loading the model (this may download weights and take time)
    try:
        model = whisper.load_model(model_name)
        device = getattr(model, "device", None)
        return {"loaded": True, "model_name": model_name, "device": str(device)}
    except Exception as e:
        return {"loaded": False, "error": str(e)}


def try_transcribe(model, audio_path: str):
    try:
        if not os.path.exists(audio_path):
            return {"success": False, "error": f"file not found: {audio_path}"}
        result = model.transcribe(audio_path)
        text = result.get("text", "") if isinstance(result, dict) else str(result)
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Check Whisper installation and optionally run a small transcription.")
    parser.add_argument("--model", default="tiny", help="Model name to load (tiny, base, small, etc.).")
    parser.add_argument("--test-audio", default=None, help="Path to an audio file to transcribe (optional).")
    parser.add_argument("--no-download", action="store_true", help="Do not download or load the model (fast import-only check).")

    args = parser.parse_args()

    print("Checking imports...")
    info = check_imports()

    print("\n== Import check ==")
    if info.get("whisper_imported"):
        print(f"whisper imported: yes (version={info.get('whisper_version')})")
    else:
        print(f"whisper imported: NO\n  error: {info.get('whisper_error')}")

    if info.get("torch_installed"):
        print(f"torch installed: yes (version={info.get('torch_version')})")
        print(f"cuda available: {info.get('cuda_available')}")
    else:
        print("torch installed: NO (optional but required for model inference)")

    if args.no_download:
        print("\nSkipping model load because --no-download was passed.")
    else:
        print(f"\nAttempting to load model '{args.model}' (may download weights and take time)...")

    model_result = try_load_model(args.model, download=not args.no_download)

    print("\n== Model load ==")
    if model_result.get("loaded") is True:
        print(f"Model loaded: {model_result.get('model_name')} on device {model_result.get('device')}")
    elif model_result.get("loaded") is None:
        print(f"Model load: skipped ({model_result.get('note')})")
    else:
        print(f"Model load failed: {model_result.get('error')}")

    # If user asked to transcribe, do it (requires the model to be loaded)
    if args.test_audio:
        print(f"\nAttempting transcription on: {args.test_audio}")
        if model_result.get("loaded") is not True:
            print("Cannot transcribe because the model was not loaded. Use --no-download only for quick checks.")
            sys.exit(3)

        # load_model again to get the model object
        try:
            import whisper as _whisper

            model = _whisper.load_model(args.model)
            tresult = try_transcribe(model, args.test_audio)
            if tresult.get("success"):
                print("\n== Transcription result ==")
                print(tresult.get("text"))
            else:
                print(f"Transcription failed: {tresult.get('error')}")
                sys.exit(4)
        except Exception:
            print("Failed to run transcription. Full traceback:")
            traceback.print_exc()
            sys.exit(5)

    print("\nCheck complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user")
        sys.exit(2)

