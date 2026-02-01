#!/usr/bin/env bash
set -euo pipefail

supervisorctl start ai-pic
supervisorctl status ai-pic
