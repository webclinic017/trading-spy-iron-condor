#!/bin/bash
#
# Tool Installer for Trading System Autonomous Orchestration
#
# This script checks for and installs required tools:
# - oh-my-codex / omx (npm package)
# - ralphex (Homebrew formula, required)
# - launchd scheduler (macOS)
#
# Usage:
#   ./install_tools.sh           # Check and install all
#   ./install_tools.sh --check   # Check only, no install
#   ./install_tools.sh --launchd # Install launchd scheduler

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../../" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# TOOL CHECKS
# ============================================================================

check_node() {
	if command -v node &>/dev/null; then
		log_info "Node.js: $(node --version)"
		return 0
	else
		log_error "Node.js not found"
		return 1
	fi
}

check_npm() {
	if command -v npm &>/dev/null; then
		log_info "npm: $(npm --version)"
		return 0
	else
		log_error "npm not found"
		return 1
	fi
}

check_brew() {
	if command -v brew &>/dev/null; then
		log_info "Homebrew: $(brew --version | head -1)"
		return 0
	else
		log_error "Homebrew not found"
		return 1
	fi
}

check_python() {
	if command -v python3 &>/dev/null; then
		log_info "Python: $(python3 --version)"
		return 0
	else
		log_error "Python3 not found"
		return 1
	fi
}

check_omx() {
	if command -v omx &>/dev/null 2>&1; then
		local version
		version=$(omx version 2>/dev/null | head -1 | awk '{print $2}')
		log_info "omx: ${version:-installed}"
		return 0
	else
		log_warn "omx not installed"
		return 1
	fi
}

version_gte() {
	# Returns 0 when version $1 >= version $2
	[[ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1)" == "$2" ]]
}

parse_ralphex_version() {
	ralphex --version 2>/dev/null | sed -nE 's/.*v([0-9]+\.[0-9]+\.[0-9]+).*/\1/p' | head -1
}

check_ralphex() {
	local min_version="0.16.0"
	if command -v ralphex &>/dev/null 2>&1; then
		local version
		version=$(parse_ralphex_version)
		if [[ -z $version ]]; then
			log_error "ralphex installed but version could not be parsed"
			return 1
		fi
		if version_gte "$version" "$min_version"; then
			log_info "ralphex: $version (meets minimum $min_version)"
			return 0
		fi
		log_warn "ralphex: $version (below minimum $min_version)"
		return 1
	else
		log_warn "ralphex not installed"
		return 1
	fi
}

check_launchd() {
	if launchctl list 2>/dev/null | grep -q "com.trading.autonomous"; then
		log_info "launchd scheduler: Running"
		return 0
	else
		log_warn "launchd scheduler: Not running"
		return 1
	fi
}

check_swarm_skill() {
	local candidates=(
		"$PROJECT_DIR/.claude/skills/swarm-orchestration/SKILL.md"
		"$HOME/.agents/skills/swarm/SKILL.md"
		"$HOME/.agents/skills/team/SKILL.md"
	)

	for skill_path in "${candidates[@]}"; do
		if [[ -f "$skill_path" ]]; then
			log_info "Swarm orchestration skill: Present (${skill_path})"
			return 0
		fi
	done

	if command -v omx >/dev/null 2>&1 && omx help 2>/dev/null | grep -q "omx team"; then
		log_info "Swarm orchestration capability: Present (omx team)"
		return 0
	fi

	log_error "Swarm orchestration skill: Missing"
	return 1
}

# ============================================================================
# INSTALLERS
# ============================================================================

install_omx() {
	log_info "Installing oh-my-codex (omx)..."
	if npm install -g oh-my-codex; then
		log_info "omx installed successfully"
		return 0
	else
		log_error "Failed to install omx"
		return 1
	fi
}

install_ralphex() {
	log_info "Installing or upgrading ralphex via Homebrew..."
	check_brew || return 1
	brew tap umputun/apps >/dev/null
	if command -v ralphex >/dev/null 2>&1; then
		brew upgrade ralphex >/dev/null || true
	else
		brew install ralphex >/dev/null
	fi
	check_ralphex
}

install_launchd() {
	local plist_src="$SCRIPT_DIR/com.trading.autonomous.plist"
	local plist_dst="$HOME/Library/LaunchAgents/com.trading.autonomous.plist"

	if [[ ! -f $plist_src ]]; then
		log_error "Plist template not found: $plist_src"
		return 1
	fi

	# Create LaunchAgents directory if needed
	mkdir -p "$HOME/Library/LaunchAgents"

	# Update plist with actual project path
	sed "s|REPLACE_WITH_PROJECT_PATH|$PROJECT_DIR|g" "$plist_src" >"$plist_dst"

	# Load the agent
	launchctl unload "$plist_dst" 2>/dev/null || true
	if launchctl load "$plist_dst"; then
		log_info "launchd scheduler installed and running"
		log_info "Logs: /tmp/trading_scheduler.log"
		return 0
	else
		log_error "Failed to load launchd agent"
		return 1
	fi
}

uninstall_launchd() {
	local plist_dst="$HOME/Library/LaunchAgents/com.trading.autonomous.plist"

	if [[ -f $plist_dst ]]; then
		launchctl unload "$plist_dst" 2>/dev/null || true
		rm -f "$plist_dst"
		log_info "launchd scheduler uninstalled"
	else
		log_warn "launchd scheduler not installed"
	fi
}

# ============================================================================
# MAIN
# ============================================================================

run_checks() {
	echo "============================================"
	echo "Trading System Tool Check"
	echo "============================================"
	echo ""

	local all_ok=true

	check_node || all_ok=false
	check_npm || all_ok=false
	check_brew || all_ok=false
	check_python || all_ok=false
	check_omx || all_ok=false
	check_ralphex || all_ok=false
	check_launchd || true # Optional, just report
	check_swarm_skill || all_ok=false

	echo ""
	if $all_ok; then
		log_info "All required tools present"
		return 0
	else
		log_warn "Some tools missing - run without --check to install"
		return 1
	fi
}

run_install() {
	echo "============================================"
	echo "Trading System Tool Installation"
	echo "============================================"
	echo ""

	# Prerequisites
	check_node || {
		log_error "Node.js required. Install via: brew install node"
		exit 1
	}

	check_npm || {
		log_error "npm required"
		exit 1
	}

	check_brew || {
		log_error "Homebrew required for ralphex. Install via: https://brew.sh"
		exit 1
	}

	check_python || {
		log_error "Python3 required. Install via: brew install python"
		exit 1
	}

	# Install required orchestration tools
	check_omx || install_omx
	check_ralphex || install_ralphex

	check_omx || {
		log_error "omx installation verification failed"
		exit 1
	}
	check_ralphex || {
		log_error "ralphex installation verification failed (requires >=0.16.0)"
		exit 1
	}

	# Verify swarm skill
	check_swarm_skill || {
		log_error "Swarm skill missing. This should be created by the orchestration system."
		exit 1
	}

	echo ""
	log_info "Tool installation complete"
	echo ""
	echo "To enable automatic scheduling, run:"
	echo "  $0 --launchd"
}

show_help() {
	echo "Trading System Tool Installer"
	echo ""
	echo "Usage: $0 [option]"
	echo ""
	echo "Options:"
	echo "  (no option)   Check and install missing tools"
	echo "  --check       Check tool status only"
	echo "  --launchd     Install and start launchd scheduler"
	echo "  --uninstall   Remove launchd scheduler"
	echo "  --help        Show this help"
}

main() {
	case "${1-}" in
	--check)
		run_checks
		;;
	--launchd)
		install_launchd
		;;
	--uninstall)
		uninstall_launchd
		;;
	--help | -h)
		show_help
		;;
	*)
		run_install
		;;
	esac
}

main "$@"
