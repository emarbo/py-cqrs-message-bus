rm -rf htmlcov
coverage run --source . -m pytest
coverage report
coverage html
xdg-open htmlcov/index.html
