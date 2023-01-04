set -xe

# for i in {1..10}; do pytest -s -x --ff $1 $2 $3 level4-1/test_http2_concurrent.py; done

pytest -x $1 $2 $3 level0
pytest -x $1 $2 $3 level1
pytest -x $1 $2 $3 level2
pytest -x $1 $2 $3 level3
pytest -x $1 $2 $3 level4
pytest -x $1 $2 $3 level4-1
pytest -x $1 $2 $3 level4-2
pytest -x $1 $2 $3 level5
