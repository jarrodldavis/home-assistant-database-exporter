#!/bin/sh
set -eu

HA_CORE_VERSION="2025.7.1"
LOG_TEMPLATE='\033[1;%sm%b\033[0m\033[1;%sm%s\033[0m\n'

printf "$LOG_TEMPLATE" 35 '--> ' 39 'Checking out Home Assistant Core...'
if ! git -C core status >/dev/null 2>&1 ; then
    git clone https://github.com/home-assistant/core.git --branch "$HA_CORE_VERSION"
else
    git -C core fetch --all --tags --prune
    git -C core checkout --force "$HA_CORE_VERSION"
    git -C core clean -xfd
fi

git -C core status

printf "$LOG_TEMPLATE" 35 '--> ' 39 'Preparing Dev Container...'
rm -rfv .devcontainer
cp -Rv core/.devcontainer .
git apply --whitespace=fix --reject devcontainer.json.patch

mkdir -pv core/config/home-assistant-database-exporter

mkdir -pv core/homeassistant/components/database_exporter
echo homeassistant/components/database_exporter >> core/.git/info/exclude
mkdir -pv core/tests/components/database_exporter
echo tests/components/database_exporter >> core/.git/info/exclude

ln -sv ../../homeassistant/components/database_exporter core/config/custom_components/database_exporter

echo 'homeassistant.components.database_exporter.*' >> core/.strict-typing
git -C core update-index --assume-unchanged .strict-typing

printf "$LOG_TEMPLATE" 32 '--> ' 39 'Done!'
