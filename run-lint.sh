#!/bin/bash

set -x

isort --recursive cq tests
black cq tests
python -m flake8 --statistics --count cq
