set -xe

pytest -s -x --ff $1 $2 $3 level5/test_grpc_async_gen.py

pytest -x $1 $2 $3 level0
pytest -x $1 $2 $3 level1
pytest -x $1 $2 $3 level2
pytest -x $1 $2 $3 level3
pytest -x $1 $2 $3 level4
pytest -x $1 $2 $3 level4-1
pytest -x $1 $2 $3 level4-2
pytest -x $1 $2 $3 level5
