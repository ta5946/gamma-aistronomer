"""gammai command line entry point."""

import argparse

from gammai import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gammai",
        description="Gamma AIstronomer: check the setup, derive use cases and run an agent analysis.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"gammai {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("help", help="show this help")
    commands.add_parser(
        "check", help="check Python, .agents.env, data, Docker, the LLM and Cognee MCP"
    )

    derive = commands.add_parser(
        "derive", help="derive science use cases and their Gammapy breakdown from Cognee MCP"
    )
    derive.add_argument("-o", "--output", help="also write the answers to this Markdown file")
    derive.add_argument(
        "-s",
        "--search-type",
        help="Cognee search type, e.g. GRAPH_COMPLETION_COT (default: Cognee's auto-routing)",
    )

    run = commands.add_parser("run", help="run an agent harness interactively or with a prompt")
    run.add_argument("harness", choices=["pi", "opencode"])
    # without a prompt or file the harness starts interactively, -i says so explicitly
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("prompt", nargs="?", help="prompt text for a one-shot run")
    mode.add_argument("-f", "--file", help="read the prompt from this file")
    mode.add_argument(
        "-i", "--interactive", action="store_true", help="start an interactive session"
    )
    run.add_argument("--force", action="store_true", help="run even if the workspace is not empty")

    args = parser.parse_args(argv)
    try:
        return dispatch(parser, run, args)
    except KeyboardInterrupt:
        return 130


def dispatch(parser, run_parser, args):
    if args.command == "help":
        parser.print_help()
        return 0

    # imported per command, so --help doesn't wait for gammapy, openai and mcp
    if args.command == "check":
        from gammai.checks import run_checks

        return run_checks()

    if args.command == "derive":
        from gammai.derive import run as run_derive

        return run_derive(args.output, args.search_type)

    prompt = args.prompt
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                prompt = f.read()
        except OSError as e:
            run_parser.error(f"cannot read {args.file}: {e.strerror}")
    if prompt is not None and not prompt.strip():
        run_parser.error("the prompt is empty")

    from gammai.run import run as run_harness

    return run_harness(args.harness, prompt, args.force)
