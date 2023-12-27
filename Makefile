install:
	pipenv install requests bleak

cleanup:
	pipenv clean

run:
	pipenv run python main.py
