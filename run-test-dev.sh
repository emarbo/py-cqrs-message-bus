#!/usr/bin/env bash
#
# This script runs tests on every Python change, and if anything fails
# it loops over failed tests one by one until de developer fixes all of them.
# The fix-loop runs pytest in "pdb mode" so the developer can easily inspect
# what's going on.
#
# This watch-fix-loop cycle is really really helpful. You can keep focus on
# each test because every test runs quite fast.
#

#
# NOTE: This script was a here-document in the entrypoint.sh injected this way:
#
# exec gosu app /bin/bash -O globstar -s <<<EOF
#     <script-here>
# EOF
#
# But since this is using the STDIN (-s) to read the script, the developer cannot
# interact with the underlying process anymore... the pipe that connects the
# docker-componse stdin and the pytest stdin was completely broken!
#
# Lesson learned: do not use -s if you want to keep the STDIN piped.
#

warning () {
    echo
    echo -e "\e[33m$1\e[0m"
    echo
}

run_tests () {
    while true
    do
        # 1. Test everything
        pytest .
        [ $? -eq 0 ] && break

        # 2.1. If failed, fix all tests one by one
        while true
        do
            warning "\n ~~ ENTERING DEBUG MODE (pdb mode) ~~ \n"
            pytest \
                --last-failed \
                --exitfirst \
                --capture=no \
                --pdb \
                --pdbcls=IPython.terminal.debugger:TerminalPdb \
                .
            [ $? -eq 0 ] && break
        done

        # 2.2 Once all tests are solved independently, loop one more time
        # to check that no new errors were introduced
    done
}

# Check inotifywait exists
if ! command -v inotifywait &> /dev/null
then
    echo ""
    echo "Install inotify-tools package to run tests looper"
    echo ""
    echo "    sudo apt install inotify-tools"
    echo ""
    exit 1
fi

# For expanding the **
shopt -s globstar

# Both inotifywait and --looponfail (pytest-xdist) do the same function
# although inotifywait makes the thing more resilient to Python
# fatal errors
while true
do
    run_tests
    inotifywait -qq -e close_write -e move_self -e create -e moved_to ./**/*.py || true
done
