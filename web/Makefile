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
	@echo "make web         - Start Next.js development server"
	@echo "make build       - Build production version"
	@echo "make start       - Start production server"
	@echo "make lint        - Run ESLint code linting"
	@echo "make lint-fix     - Run ESLint with auto-fix"
	@echo "make typecheck    - Run TypeScript type checking"
	@echo "make check        - Run both linting and type checking"
	@echo "make test        - Run unit tests"

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
.PHONY: web
web:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm dev; \
	else \
		npm run dev; \
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
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm start; \
	else \
		npm run start; \
	fi

# Linting
.PHONY: lint
lint:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm run lint; \
	else \
		npm run lint; \
	fi

# Linting with auto-fix
.PHONY: lint-fix
lint-fix:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm run lint:fix; \
	else \
		npm run lint:fix; \
	fi

# Type checking
.PHONY: typecheck
typecheck:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm run typecheck; \
	else \
		npm run typecheck; \
	fi

# Combined lint and type check
.PHONY: check
check:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm run check; \
	else \
		npm run check; \
	fi

# Run tests
.PHONY: test
test:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm test; \
	else \
		npm test; \
	fi

.DEFAULT_GOAL := help
