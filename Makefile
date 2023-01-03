develop: setup-git install-requirements

setup-git:
	pip install "pre-commit>=2.21.0,<2.22.0"
	pre-commit install
	git config branch.autosetuprebase always
	git config --bool flake8.strict true
	cd .git/hooks && ln -sf ../../hooks/* ./

install-requirements:
	pdm install
	pdm run ansible-galaxy install -r requirements.yml

all:
	pdm run ansible-playbook roles.yml

rex:
	pdm run ansible-playbook roles.yml -l rex

tower:
	pdm run ansible-playbook roles.yml -l tower

hass:
	pdm run ansible-playbook roles.yml -l rex -t hass

hass-ui:
	pdm run ansible-playbook roles.yml -l rex -t hass-ui -t tileboard

appd:
	pdm run ansible-playbook roles.yml -l rex -t appdaemon

es:
	pdm run ansible-playbook roles.yml -l rex -t es

docker:
	pdm run ansible-playbook roles.yml -l rex -t docker

dst:
	pdm run ansible-playbook roles.yml -l rex -t dst

frigate:
	pdm run ansible-playbook roles.yml -l rex -t frigate

test:
	python roles/hive.hass/files/apps/hive/base.py
