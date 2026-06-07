import argparse
import audioop
import os
import struct

import numpy as np
from PIL import Image


def databend(input_files, output_file, encoding="alaw", use_xor=False, delay_time=0.0):
    if not input_files:
        print("No input files provided.")
        return []

    # filter out non-existent files
    valid_files = [f for f in input_files if os.path.exists(f)]
    if not valid_files:
        print("No valid input files found.")
        return []

    # get dimensions and areas to find the lowest resolution
    file_dims = {}
    min_area = float("inf")
    target_w, target_h = None, None
    target_file = None

    for f in valid_files:
        try:
            with Image.open(f) as img:
                w, h = img.size
                area = w * h
                file_dims[f] = (w, h, area)
                if area < min_area:
                    min_area = area
                    target_w, target_h = w, h
                    target_file = f
        except Exception as e:
            print(f"Error reading dimensions for {f}: {e}")
            return []

    # downscale higher resolution files to match the lowest resolution file
    synced_files = []
    created_synced_files = []  # array to track newly generated downscaled files

    for f in valid_files:
        w, h, area = file_dims[f]
        if area > min_area:
            synced_name = f"{os.path.splitext(f)[0]}_synced.bmp"
            print(
                f"Downscaling {f} ({w}x{h}) to match {target_file} ({target_w}x{target_h})..."
            )
            try:
                with Image.open(f) as img:
                    resized_img = img.resize(
                        (target_w, target_h), Image.Resampling.LANCZOS
                    )
                    resized_img.save(synced_name, format="BMP")
                synced_files.append(synced_name)
                created_synced_files.append(synced_name)  # log the file path
            except Exception as e:
                print(f"Failed to resize {f}: {e}")
                return []
        else:
            synced_files.append(f)

    print(
        f"Bending {len(synced_files)} BMP file(s) | Enc: {encoding.upper()} | XOR: {use_xor} | Echo: {delay_time}s"
    )

    # extract header from the first synced file
    with open(synced_files[0], "rb") as f:
        first_file_data = f.read()

    pixel_offset = struct.unpack_from("<I", first_file_data, 10)[0]
    header = bytearray(first_file_data[:pixel_offset])

    target_byte_length = len(first_file_data) - pixel_offset

    if encoding == "adpcm":
        sample_multiplier = 2
    else:
        sample_multiplier = 1

    target_sample_length = target_byte_length * sample_multiplier

    # buffer for math
    if use_xor:
        mix_buffer = np.zeros(target_sample_length, dtype=np.int16)
    else:
        mix_buffer = np.zeros(target_sample_length, dtype=np.float32)

    # where the real shit happens
    for file in synced_files:
        with open(file, "rb") as f:
            data = f.read()
            offset = struct.unpack_from("<I", data, 10)[0]
            pixel_data = data[offset:]

            if encoding == "ulaw":
                pcm16_bytes = audioop.ulaw2lin(pixel_data, 2)
            elif encoding == "adpcm":
                pcm16_bytes, _ = audioop.adpcm2lin(pixel_data, 2, None)
            else:
                pcm16_bytes = audioop.alaw2lin(pixel_data, 2)

            if use_xor:
                audio_track = np.frombuffer(pcm16_bytes, dtype=np.int16)
            else:
                audio_track = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(
                    np.float32
                )

            if len(audio_track) > target_sample_length:
                audio_track = audio_track[:target_sample_length]
            elif len(audio_track) < target_sample_length:
                if use_xor:
                    padded = np.zeros(target_sample_length, dtype=np.int16)
                else:
                    padded = np.zeros(target_sample_length, dtype=np.float32)
                padded[: len(audio_track)] = audio_track
                audio_track = padded

            if use_xor:
                mix_buffer ^= audio_track
            else:
                mix_buffer += audio_track

    # apply delay / echo
    if delay_time > 0.0:
        delay_samples = int(delay_time * 44100)
        echo_track = np.roll(mix_buffer, delay_samples)

        if use_xor:
            mix_buffer ^= echo_track
        else:
            mix_buffer += echo_track * 0.5

    # Prepare for export
    if not use_xor:
        mix_buffer = np.clip(mix_buffer, -32768.0, 32767.0)
        mixed_pcm16_bytes = mix_buffer.astype(np.int16).tobytes()
    else:
        mixed_pcm16_bytes = mix_buffer.tobytes()

    if encoding == "ulaw":
        final_pixels = audioop.lin2ulaw(mixed_pcm16_bytes, 2)
    elif encoding == "adpcm":
        final_pixels, _ = audioop.lin2adpcm(mixed_pcm16_bytes, 2, None)
    else:
        final_pixels = audioop.lin2alaw(mixed_pcm16_bytes, 2)

    # export
    with open(output_file, "wb") as f:
        f.write(header)
        f.write(final_pixels[:target_byte_length])

    print(f"Successfully bended: {output_file}")

    # returns array of downscaled images to the caller app for deletion later
    return created_synced_files


# exec stuff
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Databend BMP files using audio algorithms."
    )
    parser.add_argument("images", nargs="+", help="Input BMP files")
    parser.add_argument(
        "-o",
        "--output",
        default="out/mash.bmp",
        help="Output BMP file (default: out/mash.bmp)",
    )
    parser.add_argument("-u", "--ulaw", action="store_true", help="Use u-law encoding")
    parser.add_argument("-a", "--adpcm", action="store_true", help="Use ADPCM encoding")
    parser.add_argument(
        "-x",
        "--xor",
        action="store_true",
        help="Use Bitwise XOR mixing instead of additive",
    )
    parser.add_argument(
        "-e", "--echo", action="store_true", help="Enable Delay/Echo effect"
    )
    parser.add_argument(
        "-n",
        "--delay_time",
        type=float,
        default=0.1,
        help="Delay time in seconds for echo (default: 0.1)",
    )

    args = parser.parse_args()

    encoding = "alaw"
    if args.adpcm:
        encoding = "adpcm"
    elif args.ulaw:
        encoding = "ulaw"

    delay_to_pass = args.delay_time if args.echo else 0.0

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    databend(
        args.images,
        args.output,
        encoding=encoding,
        use_xor=args.xor,
        delay_time=delay_to_pass,
    )
