#!/usr/bin/env python3
"""
Post sample readings from scripts/sample/readings.json to the dev API.

Usage:
    python3 scripts/seed_readings.py [--base-url URL] [--batch]

Defaults to http://localhost:8000.
Use --batch to send all readings for each sensor in a single POST to /weather/{sensor_name}/batch/.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import httpx

SAMPLE_FILE = Path(__file__).parent / 'sample' / 'readings.json'
DEFAULT_BASE_URL = 'http://localhost:8000'
ENDPOINT = '/weather/{sensor_name}/'
BATCH_ENDPOINT = '/weather/{sensor_name}/batch/'


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


def post_readings_batch(base_url: str, readings: list[dict[str, object]]) -> None:
    """Group readings by sensor and POST each group to the batch endpoint."""
    base = base_url.rstrip('/')
    created = skipped = failed = 0

    by_sensor: dict[str, list[dict[str, object]]] = defaultdict(list)
    for reading in readings:
        by_sensor[str(reading['sensorName'])].append(reading)

    for batch_index, (sensor_name, items) in enumerate(by_sensor.items(), start=1):
        url = base + BATCH_ENDPOINT.format(sensor_name=sensor_name)
        payload: dict[str, object] = {
            'items': [
                {
                    'sensorName': sensor_name,
                    'sensorDate': item['sensorDate'],
                    'dataInfo': item['dataInfo'],
                }
                for item in items
            ]
        }
        correlation_id = f'seed-batch-{batch_index:03}'
        print(f'  [{correlation_id}]  {sensor_name}  ({len(items)} item(s))')
        try:
            response = httpx.post(
                url,
                json=payload,
                headers={'X-Correlation-ID': correlation_id},
                timeout=30,
            )
        except httpx.ConnectError:
            sys.exit(f'Could not connect to {url}. Is the dev server running?')

        if response.status_code != 207:
            print(f'    [error]  status={response.status_code}  body={response.text}')
            failed += len(items)
            continue

        for result_index, result in enumerate(response.json(), start=1):
            sensor_date = items[result_index - 1]['sensorDate']
            item_status = result['status']
            if item_status == 201:
                print(f'    [created]  id={result["data"]["id"]}  {sensor_date}')
                created += 1
            elif item_status == 409:
                print(f'    [skipped]  {sensor_date}  (already exists)')
                skipped += 1
            else:
                print(f'    [failed]   {sensor_date}  status={item_status}  error={result.get("error")}')
                failed += 1

    print(f'\nDone. created={created}  skipped={skipped}  failed={failed}')
    if failed:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description='Seed sample readings into the dev API.')
    parser.add_argument('--base-url', default=DEFAULT_BASE_URL,
                        help=f'Base URL of the API (default: {DEFAULT_BASE_URL})')
    parser.add_argument('--batch', action='store_true',
                        help='Send all readings per sensor in a single batch request (POST /batch/).')
    args = parser.parse_args()

    readings: list[dict[str, object]] = json.loads(SAMPLE_FILE.read_text(encoding='utf-8'))

    if args.batch:
        print(f'Batch-posting {len(readings)} reading(s) to {args.base_url}/weather/{{sensorName}}/batch/\n')
        post_readings_batch(args.base_url, readings)
    else:
        print(f'Posting {len(readings)} reading(s) to {args.base_url}/weather/{{sensorName}}/\n')
        post_readings(args.base_url, readings)


if __name__ == '__main__':
    main()
