include .env
export

jupyter:
	# Make sure to run `poetry shell` first
	@poetry run jupyter-lab
