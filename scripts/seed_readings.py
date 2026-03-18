#!/usr/bin/env python3
"""
Post sample readings from scripts/sample/readings.json to the dev API.

Usage:
    python3 scripts/seed_readings.py [--base-url URL]

Defaults to http://localhost:8000.
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

SAMPLE_FILE = Path(__file__).parent / 'sample' / 'readings.json'
DEFAULT_BASE_URL = 'https://api-readings.thankfulwater-48ccd37b.spaincentral.azurecontainerapps.io'
ENDPOINT = '/weather/{sensor_name}/'


def post_readings(base_url: str, readings: list[dict[str, object]]) -> None:
    base = base_url.rstrip('/')
    created = skipped = failed = 0

    for index, reading in enumerate(readings, start=1):
        correlation_id = f'seed-{index:03}'
        sensor_name = reading['sensorName']
        url = base + ENDPOINT.format(sensor_name=sensor_name)
        payload = {
            'sensorName': sensor_name,
            'sensorDate': reading['sensorDate'],
            'dataInfo': reading['dataInfo'],
        }
        try:
            response = httpx.post(
                url,
                json=payload,
                headers={'X-Correlation-ID': correlation_id},
                timeout=10,
            )
        except httpx.ConnectError:
            sys.exit(f'Could not connect to {url}. Is the dev server running?')

        if response.status_code == 201:
            data = response.json()
            print(f'  [created]  [{correlation_id}]  id={data["id"]}  {payload["sensorName"]}  {payload["sensorDate"]}')
            created += 1
        elif response.status_code == 409:
            print(f'  [skipped]  [{correlation_id}]  {payload["sensorName"]}  {payload["sensorDate"]}  (already exists)')
            skipped += 1
        else:
            print(f'  [failed]   [{correlation_id}]  {payload["sensorName"]}  {payload["sensorDate"]}  '
                  f'status={response.status_code}  body={response.text}')
            failed += 1

    print(f'\nDone. created={created}  skipped={skipped}  failed={failed}')
    if failed:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description='Seed sample readings into the dev API.')
    parser.add_argument('--base-url', default=DEFAULT_BASE_URL,
                        help=f'Base URL of the API (default: {DEFAULT_BASE_URL})')
    args = parser.parse_args()

    readings: list[dict[str, object]] = json.loads(SAMPLE_FILE.read_text(encoding='utf-8'))
    print(f'Posting {len(readings)} reading(s) to {args.base_url}/weather/{{sensorName}}/\n')
    post_readings(args.base_url, readings)


if __name__ == '__main__':
    main()
