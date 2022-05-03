#!/bin/bash

set -x

isort --recursive mb tests
black mb tests
python -m flake8 --statistics --count mb
