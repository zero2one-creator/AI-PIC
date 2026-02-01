#!/usr/bin/env bash
set -euo pipefail

supervisorctl stop ai-pic
supervisorctl status ai-pic || true
