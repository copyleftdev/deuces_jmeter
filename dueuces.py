import time
import requests
import csv
import sqlite3
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor
import re


class LoadTester:
    def __init__(self, timeout: int = 5):
        self.results = []
        self.timeout = timeout

    def _sanitize_url(self, url: str) -> str:
        """Sanitize URLs to be used as filenames."""
        return re.sub(r"[^a-zA-Z0-9]", "_", url)

    def _make_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        """Make a single GET request and record the result."""
        start_time = time.time()
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            status_code = response.status_code
        except requests.RequestException as e:
            status_code = "Error"
            print(f"Error making request to {url}. Error: {e}")
        end_time = time.time()

        self.results.append(
            {
                "url": url,
                "status_code": status_code,
                "response_time": end_time - start_time,
                "timestamp": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(start_time)
                ),
            }
        )

    def simple_test(self, url: str, iterations: int = 1) -> None:
        """Perform a simple test with a given number of iterations."""
        for _ in range(iterations):
            self._make_request(url)

    def stress_test(self, url: str, concurrent_requests: int = 5) -> None:
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [
                executor.submit(self._make_request, url)
                for _ in range(concurrent_requests)
            ]
            for future in futures:
                future.result()

    def spike_test(
        self, url: str, spikes: int = 3, spike_interval: float = 1.0
    ) -> None:
        for _ in range(spikes):
            self.stress_test(url)
            time.sleep(spike_interval)

    def endurance_test(self, url: str, duration: float = 300.0) -> None:
        end_time = time.time() + duration
        while time.time() < end_time:
            self._make_request(url)

    def ramp_up_test(self, url: str, max_users: int, ramp_up_period: int) -> None:
        for i in range(1, max_users + 1):
            self.stress_test(url, i)
            time.sleep(ramp_up_period / max_users)

    def save_to_csv(self, url: str, filename: str = "results.csv") -> None:
        """Save test results to a CSV file."""
        sanitized_url = self._sanitize_url(url)
        with open(f"{sanitized_url}_{filename}", "w", newline="") as file:
            writer = csv.DictWriter(
                file, fieldnames=["url", "status_code", "response_time", "timestamp"]
            )
            writer.writeheader()
            writer.writerows(self.results)

    def save_to_sqlite(self, url: str, filename: str = "results.db") -> None:
        """Save test results to an SQLite database."""
        sanitized_url = self._sanitize_url(url)
        with sqlite3.connect(f"{sanitized_url}_{filename}") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    url TEXT,
                    status_code INTEGER,
                    response_time REAL,
                    timestamp TEXT
                )
                """
            )
            cursor.executemany(
                """
                INSERT INTO results (url, status_code, response_time, timestamp) VALUES (?, ?, ?, ?)
                """,
                [
                    (r["url"], r["status_code"], r["response_time"], r["timestamp"])
                    for r in self.results
                ],
            )


# Example usage:
if __name__ == "__main__":
    tester = LoadTester()
    test_url = "https://www.example.com"
    tester.ramp_up_test(test_url, max_users=10, ramp_up_period=10)
    tester.save_to_csv(test_url)
    tester.save_to_sqlite(test_url)
