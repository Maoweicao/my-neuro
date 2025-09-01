#!/usr/bin/env python3
import argparse
import json
import logging
import uuid

import websockets

from protocols import EventType, MsgType, full_client_request, receive_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_resource_id(voice: str) -> str:
    if voice.startswith("S_"):
        return "volc.megatts.default"
    return "volc.service_type.10029"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--appid", required=True, help="APP ID")
    parser.add_argument("--access_token", required=True, help="Access Token")
    parser.add_argument("--resource-id", default="", help="Resource ID")
    parser.add_argument("--text", required=True, help="Text to convert")
    parser.add_argument("--voice_type", default="", required=True, help="Voice type")
    parser.add_argument("--encoding", default="wav", help="Output file encoding")
    parser.add_argument(
        "--endpoint",
        default="wss://openspeech.bytedance.com/api/v3/tts/unidirectional/stream",
        help="WebSocket endpoint URL",
    )

    args = parser.parse_args()

    # Connect to server
    headers = {
        "X-Api-App-Key": args.appid,
        "X-Api-Access-Key": args.access_token,
        "X-Api-Resource-Id": (
            args.resource_id if args.resource_id else get_resource_id(args.voice_type)
        ),
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }

    logger.info(f"Connecting to {args.endpoint} with headers: {headers}")
    websocket = await websockets.connect(
        args.endpoint, additional_headers=headers, max_size=10 * 1024 * 1024
    )
    logger.info(
        f"Connected to WebSocket server, Logid: {websocket.response.headers['x-tt-logid']}",
    )

    try:
        # Prepare request payload
        request = {
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "req_params": {
                "speaker": args.voice_type,
                "audio_params": {
                    "format": args.encoding,
                    "sample_rate": 24000,
                    "enable_timestamp": True,
                },
                "text": args.text,
                "additions": json.dumps(
                    {
                        "disable_markdown_filter": False,
                    }
                ),
            },
        }

        # Send request
        await full_client_request(websocket, json.dumps(request).encode())

        # Receive audio data
        audio_data = bytearray()
        while True:
            msg = await receive_message(websocket)

            if msg.type == MsgType.FullServerResponse:
                if msg.event == EventType.SessionFinished:
                    break
            elif msg.type == MsgType.AudioOnlyServer:
                audio_data.extend(msg.payload)
            else:
                raise RuntimeError(f"TTS conversion failed: {msg}")

        # Check if we received any audio data
        if not audio_data:
            raise RuntimeError("No audio data received")

        # Save audio file
        filename = f"{args.voice_type}.{args.encoding}"
        with open(filename, "wb") as f:
            f.write(audio_data)
        logger.info(f"Audio received: {len(audio_data)}, saved to {filename}")

    finally:
        await websocket.close()
        logger.info("Connection closed")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
