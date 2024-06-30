# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Splits a response into atomic facts."""

import logging
import itertools
from typing import Any

# pylint: disable=g-bad-import-order
from common import modeling
from third_party.factscore import atomic_facts
# pylint: enable=g-bad-import-order

_SENTENCE = 'sentence'
_ATOMIC_FACTS = 'atomic_facts'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_atomic_facts_to_dicts(
    outputted_facts: list[tuple[str, list[str]]]
) -> list[dict[str, Any]]:
    logging.info("Converting outputted facts to dictionaries.")
    converted_dicts = [
        {_SENTENCE: sentence, _ATOMIC_FACTS: identified_atomic_facts}
        for sentence, identified_atomic_facts in outputted_facts
    ]
    logging.info("Conversion complete.")
    return converted_dicts

def main(response: str, model: modeling.Model) -> dict[str, Any]:
    logging.info("Starting main function for fetching atomic facts.")
    atomic_fact_generator = atomic_facts.AtomicFactGenerator(
        api_key='', gpt3_cache_file='', other_lm=model
    )
    try:
        facts, _ = atomic_fact_generator.run(response)
        logging.info("Atomic facts generated successfully.")
    except Exception as e:
        logging.error(f"Failed to generate atomic facts: {e}")
        raise

    facts_as_dict = convert_atomic_facts_to_dicts(facts)
    all_atomic_facts = list(
        itertools.chain.from_iterable([f[_ATOMIC_FACTS] for f in facts_as_dict])
    )
    result = {
        'num_claims': len(all_atomic_facts),
        'sentences_and_atomic_facts': facts,
        'all_atomic_facts': facts_as_dict,
    }
    logging.info("Main function completed for fetching atomic facts.")
    return result
