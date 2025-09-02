# SlideSpeaker Web Makefile

# Variables
NPM := npm
PNPM := pnpm

# Default target
.PHONY: help
help:
	@echo "SlideSpeaker Web - Makefile Commands"
	@echo "================================"
	@echo "make install     - Install dependencies (uses pnpm if available, falls back to npm)"
	@echo "make dev         - Start development server"
	@echo "make build       - Build production version"
	@echo "make start       - Start production server (serve build)"

# Install dependencies
.PHONY: install
install:
	@if command -v pnpm >/dev/null 2>&1; then \
		echo "Using pnpm to install dependencies..."; \
		pnpm install; \
	else \
		echo "Using npm to install dependencies..."; \
		npm install; \
	fi

# Development server
.PHONY: dev
dev:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm start; \
	else \
		npm start; \
	fi

# Build production version
.PHONY: build
build:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm build; \
	else \
		npm run build; \
	fi

# Start production server
.PHONY: start
start:
	npm install -g serve
	serve -s build

.DEFAULT_GOAL := help