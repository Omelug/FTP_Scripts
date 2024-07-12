venv_init:
	python3 -m venv .venv

venv_clean:
	rm  -rf .venv

req_save:
	pip3 freeze > requirements.txt

install:
	pip3 install -r requirements.txt
	pip3 install git+https://github.com/Omelug/python_mini_modules.git#egg=input_parser