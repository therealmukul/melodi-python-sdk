import os
import re
import requests
import logging
import json
from typing import Optional

from .exceptions import MelodiAPIError


class MelodiClient:
    def __init__(self, api_key: Optional[str] = None, verbose=False):
        self.api_key = api_key or os.environ.get("MELODI_API_KEY")

        if not self.api_key:
            raise MelodiAPIError(
                "API key not found. Set the MELODI_API_KEY environment "
                "variable or pass it as an argument."
            )

        self.base_url = "https://app.melodi.fyi/api/external/experiments"
        self.url = self.base_url + f"?apiKey={self.api_key}"
        self.logger = logging.getLogger(__name__)

        if verbose:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.ERROR)

    @staticmethod
    def _get_headers():
        return {"Content-Type": "application/json"}

    def _send_request(self, request_data):
        response = None

        try:
            response = requests.post(
                self.url, headers=self._get_headers(), json=request_data
            )
            response.raise_for_status()
            self.logger.info("Successfully create Melodi experiment.")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create Melodi experiment: {e}")

        if response and response.status_code == 200:
            try:
                feedback_url = response.json().get("feedbackUrl")
                match = re.search(r"(\d+)$", feedback_url)
                exp_id = int(match.group(1))
                self.logger.info(
                    f"Experiment ID: {exp_id}",
                )
            except MelodiAPIError as e:
                raise MelodiAPIError(f"{e}")
        else:
            self.logger.error("Failed to extract experiment ID")

    def load_samples(self, file_path: str, experiment_type: str) -> list:
        res = []
        self.logger.info(msg=f"Loading samples from: {file_path}")

        if experiment_type == "binary":
            self.logger.info(f"Experiment type = binary")
            with open(file_path, "r") as file:
                for line in file:
                    json_object = json.loads(line.strip())

                    if "response" not in json_object:
                        raise Exception(
                            f'Sample {json_object} is missing "response" ' f"attribute."
                        )

                    res.append(json_object)

        elif experiment_type == "bake_off":
            self.logger.info(f"Experiment type = bake-off")
            with open(file_path, "r") as file:
                for line in file:
                    json_object = json.loads(line.strip())
                    samples = json_object["samples"]

                    for sample in samples:
                        if "response" not in sample:
                            raise Exception(
                                f'Sample {sample} is missing "response" ' f"attribute."
                            )

                        elif "promptLabel" not in sample:
                            raise Exception(
                                f'Sample {sample} is missing "promptLabel" '
                                f"attribute."
                            )

                    res.append(json_object)

        self.logger.info(msg=f"Loaded {len(res)} samples")

        return res

    def create_binary_evaluation_experiment(
        self,
        name: str,
        samples: list,
        instructions: Optional[str] = None,
        project: Optional[str] = None,
    ) -> None:
        if not name:
            raise ValueError("Experiment name is required.")

        request_data = {
            "experiment": {
                "name": name,
                "instructions": instructions,
                "project": project,
            },
            "samples": samples,
        }

        self._send_request(request_data=request_data)

    def create_bake_off_evaluation_experiment(
        self,
        name: str,
        comparisons: list,
        instructions: Optional[str] = None,
        project: Optional[str] = None,
    ) -> None:
        if not name:
            raise ValueError("Experiment name is required.")

        request_data = {
            "experiment": {
                "name": name,
                "instructions": instructions,
                "project": project,
            },
            "comparisons": comparisons,
        }

        self._send_request(request_data=request_data)

    def make_shareable(self, experiment_id: int) -> Optional[str]:
        url = f"{self.base_url}/{experiment_id}/shareable-link?apiKey={self.api_key}"
        response = requests.post(url)

        return (
            response.json().get("shareableLink")
            if response.status_code == 200
            else None
        )
