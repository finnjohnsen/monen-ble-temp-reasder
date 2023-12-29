install:
	pipenv install requests bleak paho-mqtt

cleanup:
	pipenv clean

run:
	pipenv run python main.py





