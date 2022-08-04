pytest -x --ff $1 $2 $3 level0 && \
pytest -x --ff $1 $2 $3 level1 && \
pytest -x --ff $1 $2 $3 level2 && \
pytest -x --ff $1 $2 $3 level3 && \
pytest -x --ff $1 $2 $3 level4 && \
pytest -x --ff $1 $2 $3 level4-1 && \
pytest -x --ff $1 $2 $3 level4-2 && \
pytest -x --ff $1 $2 $3 level5
