#!/usr/bin/env bash
# Build the Android debug APK into bin/.
# Needs: JDK 17 (~/.jdks/temurin-17) and buildozer installed in .venv-buildozer
#   python -m venv .venv-buildozer && .venv-buildozer/bin/pip install buildozer cython setuptools
set -euo pipefail
cd "$(dirname "$0")"

export JAVA_HOME="${JAVA_HOME_17:-$HOME/.jdks/temurin-17}"
export VIRTUAL_ENV="$PWD/.venv-buildozer"   # makes buildozer install its helpers into this venv, not --user
export PATH="$JAVA_HOME/bin:$VIRTUAL_ENV/bin:$PATH"
export PIP_CONSTRAINT="$PWD/android-constraints.txt"

# python-for-android re-runs "python -m venv" over its helper venv on every build, which mixes the bundled pip
# with the previously upgraded one and breaks pip; start each build with a fresh helper venv instead.
rm -rf .buildozer/android/platform/build-*/build/venv

buildozer -v android "${1:-debug}"
