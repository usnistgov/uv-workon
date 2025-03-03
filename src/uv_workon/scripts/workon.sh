# shellcheck disable=SC2148,SC1090
# Inspired by https://github.com/sitic/uv-virtualenvwrapper/blob/main/uv-virtualenvwrapper.sh
# Windows use 'Scripts' instead of 'bin'
VIRTUALENVWRAPPER_ENV_BIN_DIR="bin"
if [ "${OS:-}" = "Windows_NT" ] && { [ "${MSYSTEM:-}" = "MINGW32" ] || [ "${MSYSTEM:-}" = "MINGW64" ]; }; then
    # Only assign this for msys, cygwin uses 'bin'
    VIRTUALENVWRAPPER_ENV_BIN_DIR="Scripts"
fi

uv-workon-activate() {
    if [ $# -eq 0 ]; then
        uv-workon list
        return 0
    fi

    local WORKON_HOME="${WORKON_HOME:-$HOME/.virtualenvs}"
    local venv_name="$1"
    local venv_path="$WORKON_HOME/$venv_name"

    if [ -f "$venv_path/$VIRTUALENVWRAPPER_ENV_BIN_DIR/activate" ]; then
        source "$venv_path/$VIRTUALENVWRAPPER_ENV_BIN_DIR/activate"
    elif [ -f "$venv_name/$VIRTUALENVWRAPPER_ENV_BIN_DIR/activate" ]; then
        source "$venv_name/$VIRTUALENVWRAPPER_ENV_BIN_DIR/activate"
    elif [ -f "$venv_name/.venv/$VIRTUALENVWRAPPER_ENV_BIN_DIR/activate" ]; then
        source "$venv_name/.venv/$VIRTUALENVWRAPPER_ENV_BIN_DIR/activate"
    else
        echo "Virtualenv '$venv_name' not found in $WORKON_HOME" >&2
        return 1
    fi
}
