# Panopoly manages building and running projects of software packages across different source and run environments.

## Packaging

This Python package is managed by `uv`, uses Click for CLI, provides a Python module and has pytest unit tests. 

```
uv sync  # update after pyproject.toml changes
uv run panopoly [...] # run CLI in place
uv run pytest [...]   # run tests
```

## Development

Follow these development guidelines:

- DRY: don't repeat yourself by factoring common code to functions or classes, do not engage in copy-paste style.

- Avoid extended greenfield implementation for features that can be provided by a new dependency.  Discuss with the human before adding a dependency.

- Use XDG standards for finding file locations.

- CLI should accept a configuration file in TOML format.  A Python module may be developed to support configuration but the rest of the Python modules' functions should be given objects that are constructed by the CLI layer and not directly know about configuration files.  General configuration override precedence, from weak to strong is: environment variables -> configuration file -> command line option.

- Use Python logging instead of `print()` for diagnostics.  Use top level CLI options to set log level and log sink, default to stderr and "info" level.  Only use stdout in CLI command functions and for cases where stdout is delivering operational output.

- CLI commands lacking arguments or with explicitly `-h/--help` should generally produce "help" output.  Some CLI commands that should be operational with no arguments are excluded as special cases.

- Plan and develop using Beads issues via the `bd` command, see below.

- Write and exercise code-level and CLI-level tests.  Tests should be written and pass before an issue is closed.

- Use of `git commit` is allowed but leave `git push` to the human.  The human may instruct not to use `git commit` for the session.

## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work before starting
bd update <id> --notes="suppplementary info"  # lessons learned or other new info about the issue
bd close <id> --reason="explanation"  #  Why/how the issue has been addressed.
bd create --title="Summary of issue" --description="Longer narrative" --type=epic|task|bug|feature # Make any new issues with enough context to work them 
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` liberally for persistent knowledge — do NOT use MEMORY.md files

