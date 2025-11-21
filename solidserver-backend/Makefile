SHELL := /bin/bash

# Directory containing the package to build
PKG_DIR := $(shell pwd)

PYTHON := python3
PIP := $(PYTHON) -m pip
BUILD_CMD := $(PYTHON) -m build --wheel --outdir dist

.PHONY: all wheel clean clean-dist help

all: wheel

help:
	@echo "Makefile targets (run inside solidserver-backend/):"
	@echo "  make wheel      -- build only the wheel into ./dist"
	@echo "  make clean      -- remove build/ and *.egg-info"
	@echo "  make clean-dist -- remove dist/ (wheels)"

wheel:
	@echo "Building wheel into ./dist using pip wheel (no global installs)"
	mkdir -p dist
	# Use pip wheel to build in an isolated environment; this does not modify
	# the system/site-packages, it only downloads build-time deps into a
	# temporary isolated environment and produces a wheel in ./dist.
	$(PYTHON) -m pip wheel . -w dist
	@echo "Wheel built in: $(PKG_DIR)/dist"

clean:
	@echo "Removing build artifacts"
	rm -rf build *.egg-info ./*.egg-info

clean-dist:
	@echo "Removing dist (wheels)"
	rm -rf dist
