"""GameBored entry point: `python -m gamebored` or the `GameBored` launcher."""

import sys


def main(argv=None):
    from .app import run

    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help", "help"):
        print("GameBored: pick a game, play, come back. q/Esc quits.")
        print("Usage: GameBored [--help] [--version] [--list]")
        return 0
    if argv and argv[0] == "--version":
        from . import __version__

        print("GameBored %s" % __version__)
        return 0
    if argv and argv[0] == "--list":
        from .games import GAMES

        for i, mod in enumerate(GAMES, 1):
            print("%2d. %-12s %s" % (i, mod.TITLE, mod.DESCRIPTION))
        print(" W. Bored Wondering Search the web, keyless")
        print(" H. High Scores   Every best in raw + Bored Points")
        print(" T. Score Translator Raw number -> BP for any game")
        print(" ?. Help           How to play everything")
        return 0
    from .app import run

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
