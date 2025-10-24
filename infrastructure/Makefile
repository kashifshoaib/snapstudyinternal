# SnapStudy Infrastructure Makefile

# Default environment
ENV ?= dev
PROFILE ?=
REGION ?= us-east-1

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Helper function to print colored output
define print_info
	@echo -e "$(BLUE)ℹ️  $(1)$(NC)"
endef

define print_success
	@echo -e "$(GREEN)✅ $(1)$(NC)"
endef

define print_warning
	@echo -e "$(YELLOW)⚠️  $(1)$(NC)"
endef

define print_error
	@echo -e "$(RED)❌ $(1)$(NC)"
endef

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help: ## Show this help message
	@echo "SnapStudy Infrastructure Management"
	@echo "=================================="
	@echo ""
	@echo "Usage: make [target] [ENV=environment] [PROFILE=aws-profile]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  make deploy ENV=dev"
	@echo "  make deploy ENV=prod PROFILE=production"
	@echo "  make test"
	@echo "  make clean"

# Setup and installation
.PHONY: install
install: ## Install dependencies
	$(call print_info,"Installing dependencies...")
	npm install
	$(call print_success,"Dependencies installed!")

.PHONY: setup
setup: install ## Setup the project (install dependencies and run initial checks)
	$(call print_info,"Setting up project...")
	@make check-tools
	@make check-aws
	$(call print_success,"Project setup complete!")

# Development targets
.PHONY: build
build: ## Build the project
	$(call print_info,"Building project...")
	npm run build
	$(call print_success,"Build complete!")

.PHONY: test
test: ## Run tests
	$(call print_info,"Running tests...")
	npm test
	$(call print_success,"Tests passed!")

.PHONY: lint
lint: ## Run linting
	$(call print_info,"Running linter...")
	npm run lint || true
	$(call print_success,"Linting complete!")

.PHONY: clean
clean: ## Clean build artifacts
	$(call print_info,"Cleaning build artifacts...")
	rm -rf node_modules
	rm -rf cdk.out
	rm -rf coverage
	rm -rf dist
	$(call print_success,"Clean complete!")

# CDK targets
.PHONY: synth
synth: build ## Synthesize CloudFormation template
	$(call print_info,"Synthesizing CloudFormation template for $(ENV)...")
	@if [ -n "$(PROFILE)" ]; then \
		export AWS_PROFILE=$(PROFILE); \
	fi; \
	export ENVIRONMENT=$(ENV); \
	cdk synth
	$(call print_success,"Synthesis complete!")

.PHONY: diff
diff: build ## Show differences between deployed stack and current code
	$(call print_info,"Showing differences for $(ENV)...")
	@if [ -n "$(PROFILE)" ]; then \
		export AWS_PROFILE=$(PROFILE); \
	fi; \
	export ENVIRONMENT=$(ENV); \
	cdk diff || true

.PHONY: bootstrap
bootstrap: ## Bootstrap CDK in the target account/region
	$(call print_info,"Bootstrapping CDK...")
	@if [ -n "$(PROFILE)" ]; then \
		export AWS_PROFILE=$(PROFILE); \
	fi; \
	cdk bootstrap
	$(call print_success,"Bootstrap complete!")

# Deployment targets
.PHONY: pre-deploy
pre-deploy: ## Run pre-deployment checks
	$(call print_info,"Running pre-deployment checks...")
	chmod +x scripts/pre-deploy-check.sh
	./scripts/pre-deploy-check.sh

.PHONY: deploy
deploy: pre-deploy build test ## Deploy infrastructure
	$(call print_info,"Deploying to $(ENV)...")
	chmod +x scripts/deploy-with-config.sh
	@if [ -n "$(PROFILE)" ]; then \
		./scripts/deploy-with-config.sh -e $(ENV) -p $(PROFILE); \
	else \
		./scripts/deploy-with-config.sh -e $(ENV); \
	fi
	$(call print_success,"Deployment complete!")

.PHONY: deploy-fast
deploy-fast: build ## Deploy without tests and checks (use with caution)
	$(call print_warning,"Fast deployment - skipping tests and checks!")
	chmod +x scripts/deploy-with-config.sh
	@if [ -n "$(PROFILE)" ]; then \
		./scripts/deploy-with-config.sh -e $(ENV) -p $(PROFILE) --skip-tests --skip-confirmation; \
	else \
		./scripts/deploy-with-config.sh -e $(ENV) --skip-tests --skip-confirmation; \
	fi

.PHONY: rollback
rollback: ## Rollback infrastructure
	$(call print_warning,"Rolling back $(ENV)...")
	chmod +x scripts/rollback.sh
	@if [ -n "$(PROFILE)" ]; then \
		./scripts/rollback.sh -e $(ENV) -p $(PROFILE); \
	else \
		./scripts/rollback.sh -e $(ENV); \
	fi

.PHONY: destroy
destroy: ## Destroy infrastructure (use with extreme caution)
	$(call print_error,"Destroying $(ENV) infrastructure...")
	@if [ "$(ENV)" = "prod" ]; then \
		echo "$(RED)⚠️  PRODUCTION DESTRUCTION BLOCKED$(NC)"; \
		echo "Use 'make force-destroy ENV=prod' if you really want to destroy production"; \
		exit 1; \
	fi
	chmod +x scripts/destroy.sh
	./scripts/destroy.sh

.PHONY: force-destroy
force-destroy: ## Force destroy infrastructure (including production)
	$(call print_error,"Force destroying $(ENV) infrastructure...")
	chmod +x scripts/destroy.sh
	ENVIRONMENT=$(ENV) ./scripts/destroy.sh

# Validation and monitoring
.PHONY: validate
validate: ## Validate deployed infrastructure
	$(call print_info,"Validating deployment...")
	chmod +x scripts/validate-deployment.sh
	./scripts/validate-deployment.sh
	$(call print_success,"Validation complete!")

.PHONY: status
status: ## Show stack status
	$(call print_info,"Checking stack status for $(ENV)...")
	@if [ -n "$(PROFILE)" ]; then \
		export AWS_PROFILE=$(PROFILE); \
	fi; \
	STACK_NAME=$$(jq -r ".$(ENV).stackName" config/environments.json 2>/dev/null || echo "SnapStudy-$(ENV)"); \
	aws cloudformation describe-stacks --stack-name "$$STACK_NAME" --region $(REGION) --query 'Stacks[0].[StackName,StackStatus,CreationTime,LastUpdatedTime]' --output table || echo "Stack not found"

.PHONY: outputs
outputs: ## Show stack outputs
	$(call print_info,"Showing stack outputs for $(ENV)...")
	@if [ -n "$(PROFILE)" ]; then \
		export AWS_PROFILE=$(PROFILE); \
	fi; \
	STACK_NAME=$$(jq -r ".$(ENV).stackName" config/environments.json 2>/dev/null || echo "SnapStudy-$(ENV)"); \
	aws cloudformation describe-stacks --stack-name "$$STACK_NAME" --region $(REGION) --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue,Description]' --output table || echo "Stack not found"

.PHONY: events
events: ## Show recent stack events
	$(call print_info,"Showing recent stack events for $(ENV)...")
	@if [ -n "$(PROFILE)" ]; then \
		export AWS_PROFILE=$(PROFILE); \
	fi; \
	STACK_NAME=$$(jq -r ".$(ENV).stackName" config/environments.json 2>/dev/null || echo "SnapStudy-$(ENV)"); \
	aws cloudformation describe-stack-events --stack-name "$$STACK_NAME" --region $(REGION) --max-items 20 --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' --output table || echo "Stack not found"

# Environment-specific shortcuts
.PHONY: deploy-dev
deploy-dev: ## Deploy to development environment
	@make deploy ENV=dev

.PHONY: deploy-staging
deploy-staging: ## Deploy to staging environment
	@make deploy ENV=staging

.PHONY: deploy-prod
deploy-prod: ## Deploy to production environment
	@make deploy ENV=prod

# Utility targets
.PHONY: check-tools
check-tools: ## Check if required tools are installed
	$(call print_info,"Checking required tools...")
	@command -v node >/dev/null 2>&1 || { $(call print_error,"Node.js is not installed"); exit 1; }
	@command -v npm >/dev/null 2>&1 || { $(call print_error,"npm is not installed"); exit 1; }
	@command -v aws >/dev/null 2>&1 || { $(call print_error,"AWS CLI is not installed"); exit 1; }
	@command -v cdk >/dev/null 2>&1 || { $(call print_error,"AWS CDK is not installed"); exit 1; }
	@command -v jq >/dev/null 2>&1 || { $(call print_error,"jq is not installed"); exit 1; }
	$(call print_success,"All required tools are installed!")

.PHONY: check-aws
check-aws: ## Check AWS credentials and permissions
	$(call print_info,"Checking AWS credentials...")
	@aws sts get-caller-identity >/dev/null 2>&1 || { $(call print_error,"AWS credentials not configured"); exit 1; }
	$(call print_success,"AWS credentials are valid!")

.PHONY: list-stacks
list-stacks: ## List all SnapStudy stacks
	$(call print_info,"Listing SnapStudy stacks...")
	@if [ -n "$(PROFILE)" ]; then \
		export AWS_PROFILE=$(PROFILE); \
	fi; \
	aws cloudformation list-stacks --region $(REGION) --query 'StackSummaries[?contains(StackName, `SnapStudy`) && StackStatus != `DELETE_COMPLETE`].[StackName,StackStatus,CreationTime]' --output table

.PHONY: cost-estimate
cost-estimate: synth ## Estimate deployment costs (requires AWS Cost Calculator)
	$(call print_info,"Generating cost estimate...")
	$(call print_warning,"Cost estimation requires manual analysis of the synthesized template")
	$(call print_info,"Check cdk.out/ directory for CloudFormation templates")
	$(call print_info,"Use AWS Cost Calculator: https://calculator.aws/")

# Documentation targets
.PHONY: docs
docs: ## Generate documentation
	$(call print_info,"Generating documentation...")
	@echo "Documentation targets:"
	@echo "- README.md: Project overview"
	@echo "- DEPLOYMENT.md: Deployment guide"
	@echo "- Architecture diagrams in docs/"
	$(call print_success,"Documentation ready!")

# Development workflow shortcuts
.PHONY: dev-setup
dev-setup: setup bootstrap ## Complete development setup
	$(call print_success,"Development environment ready!")

.PHONY: dev-deploy
dev-deploy: ## Quick development deployment
	@make deploy-fast ENV=dev

.PHONY: dev-test
dev-test: build test validate ## Run full development test suite
	$(call print_success,"Development tests complete!")

# CI/CD targets
.PHONY: ci-test
ci-test: install build test ## CI test pipeline
	$(call print_success,"CI tests passed!")

.PHONY: ci-deploy
ci-deploy: ci-test ## CI deployment pipeline
	@make deploy ENV=$(ENV) --skip-confirmation

# Maintenance targets
.PHONY: update-deps
update-deps: ## Update dependencies
	$(call print_info,"Updating dependencies...")
	npm update
	npm audit fix || true
	$(call print_success,"Dependencies updated!")

.PHONY: security-scan
security-scan: ## Run security scan
	$(call print_info,"Running security scan...")
	npm audit
	$(call print_success,"Security scan complete!")

# Backup and restore (for production)
.PHONY: backup-config
backup-config: ## Backup configuration
	$(call print_info,"Backing up configuration...")
	mkdir -p backups
	cp -r config/ backups/config-$(shell date +%Y%m%d-%H%M%S)/
	$(call print_success,"Configuration backed up!")

# Environment info
.PHONY: env-info
env-info: ## Show environment information
	@echo "Environment Information:"
	@echo "======================="
	@echo "Environment: $(ENV)"
	@echo "Profile: $(PROFILE)"
	@echo "Region: $(REGION)"
	@echo "Node.js: $$(node --version 2>/dev/null || echo 'Not installed')"
	@echo "npm: $$(npm --version 2>/dev/null || echo 'Not installed')"
	@echo "AWS CLI: $$(aws --version 2>/dev/null || echo 'Not installed')"
	@echo "CDK: $$(cdk --version 2>/dev/null || echo 'Not installed')"
	@echo "jq: $$(jq --version 2>/dev/null || echo 'Not installed')"
	@if [ -n "$(PROFILE)" ]; then \
		echo "AWS Account: $$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'Not configured')"; \
	fi