I want a Python script named `panopoly` using Click for the API and that will help me manage a development area that I want use for building, testing and running of a variety of projects each consisting of overlapping subsets of source provided as git worktrees from a shared set of bare git repos.

What follows is a lengthy specification for what this script should provide.  Read it carefully, ask any questions, then make a plan with Beads and we will then implement that plan.

First I describe the layout of an example panopoly area.  

The area consists of three main sub-directories

- `source/` holds bare git repos 
- `project/` holds a sub-directory for each project, a `project/<proj>/src/` holds a git worktree for each in a subset of the source repos.
- `env/` holds named sub-directories, each with a common sub-structure and each relevant to a particular run-time environment.  An environment may be a native host or intended to be run from a podman container.  `panopoly` configuration is used to map a name to information on how to enter the environment.

Next I give a file system tree diagram for one example layout.  The top-level `dev/` name is arbitrary and is the root of the panopoly area.
The example assumes three source repos (`repoA`, `repoB`, `repoC`) and two projects (`projX`, `projY`) and three environments (`host`, `e19`, `ubuntu24`).  


```
dev/
├── source/                         # ── shared across ALL environments
│   ├── repoA.git/                  #    bare clones (the hub)
│   ├── repoB.git/
│   └── repoC.git/
│
├── project/                        # ── per-project, environment-agnostic
│   ├── projX/
│   │   ├── src/                    #    worktrees live here
│   │   │   ├── repoA  ->  repoA.git worktree
│   │   │   └── repoB  ->  repoB.git worktree
│   │   └── .envrc                  #    top-level direnv: sets PROJECT=projX etc
│   └── projY/
│       ├── src/
│       │   ├── repoB  ->  repoB.git worktree
│       │   └── repoC  ->  repoC.git worktree
│       └── .envrc
│
└── env/                            # ── per-environment, potentially per-project
    ├── .envrc                      #    env-level direnv
    ├── host/
    │   ├── spack/                  #    Spack installation for host, or symink to it.
    │   ├── views/
    │   │   ├── projX/              #    Spack view: projX deps on host
    │   │   └── projY/              #    Spack view: projY deps on host
    │   ├── build/
    │   │   ├── projX/
    │   │   │   ├── repoA/              #    cmake/make build dir for repoA
    │   │   │   └── repoB/
    │   │   └── projY/
    │   │       ├── repoB/
    │   │       └── repoC/
    │   └── run/                    #    direnv overlays for host
    │       ├── projX/
    │       │   └── .envrc          #    sources host view, sets build paths
    │       └── projY/
    │           └── .envrc
    │
    ├── el9/                        # ── one subtree per container image
    │   ├── spack/
    │   ├── views/
    │   │   ├── projX/
    │   │   └── projY/
    │   ├── build/
    │   │   ├── projX/
    │   │   └── projY/
    │   └── run/
    │       ├── projX/
    │       └── projY/
    │
    └── ubuntu24/
        ├── spack/
        ├── views/
        ├── build/
        └── run/
```

Notes on path patterns:

- `project/<proj>/src/<repo>/` git worktree of `<repo>` for project `<proj>`
- `env/<env>/spack` a root to a Spack installation area, or a symlink to one.
- `env/<env>/views/<proj>/` a Spack View providing build deps the project `<proj>` in the environment `<env>`.
- `env/<env>/build/<proj>/<repo>/` receive build proejcts for the repo, in the project in the environment.
- `env/<env>/run/<proj>/.envrc` the runtime shell environment configuration to use all this

Here is an example how a container environment would be started:

```
podman run \
  -v /path/to/dev/project:/project:ro \       # all source, read-only
  -v /path/to/dev/env/el9:/env:rw \           # this env's spack/views/build/run
  my-el9-image
```

The image name is assumed to be the `<env>` in `env/<env>/` unless a `config.toml` entry of `[env.<env>]` provides an `image` setting.  This and other configuration may be provided by a `panopoly` configuration file  in `~/.config/panopoly/config.toml`.

Note, the `source/` volume is not mounted in the container.  The user will do any `git` operations from the host.

There are three types of `.envrc`: "project" for things related to a projects source worktrees, "env" related to things generally about an environment, and "run" related about a specific project in the environment

All `.envrc` should set variables based on relative internal paths but expand those to absolute paths.

In a project-level `project/<proj>/.envrc` define these:

- `PANOPOLY_PROJECT` names the project
- `PANOPOLY_WORKTREES` gives a :-separated `PATH`-like variable listing the top level source worktrees paths.
- `PANOPOLY_WORKTREE_<src>` gives the path to the source `<src>` worktree eg `

In an env-level `env/<env>/.envrc` define these

- `PANOPOLY_SPACK` to point to the `spack/` directory
- Add `$PANOPOLY_SPACK/bin` to `PATH` (do not source spack's "setup" script).

In a run-level `env/<env>/run/<proj>/.envrc` define these

- Include the corresponding project level `.envrc`
- `PANOPOLY_PREFIX` gives the project's view directory `env/<env>/views/<proj>/`
- `load_prefix $PANOPOLY_PREFIX` defines standard variables on that prefix
- 

To the extent possible, the `.envrc` files should be written generically so that they discover identifiers based on their file system context.  Eg a project-level `.envrc` can enumerate `src/*/` directories, it and the run-level can learn the project from the current working directory.

The `config.toml` may provide additional `.envrc` file content with TOML sections matching the path.  Eg `[project/projY/.envrc]`.

Here are some of the initial Click sub-commands that the `panopoly` script should provide.  They generally should operate in an idempotent manner.

- `init` : create a skeleton of a panopoly tree in the directory given on the command line or the current directory if non is given.  By default, this simply makes `source/`, `project/` and `/env` directories.  An optional `--layout` can give a layout name that if defined in `config.toml` like `[layout.<layoutname>]` more details are given.  The variables `sources` gives a list of git remote URLs from which to create the bare git clones, a `projects` names a list of `[project.<projectname>]` sections to initialize one or more areas under `project/` and `envs` a list of `[env.<envname>]` config sections.  Dispatching parts of this config information will be the job of other commands and `init` should delegate to those commands or call high-level functions shared by those commands.

- `source add <giturl>` add git remote to the `source/` area.

- `project add <projectname> [<sourcename> ...]` add named project skeleton to the tree, if `[project.<projectname>]` section is in the config, use that to add additional information.  If one or more `<sourcename>` is given, narrow the action to just those sources.

- `env add <envname> [<projname> ...]` add a named environment skeleton to the tree, if `[env.<envname>]` section is in the config, use that to add additional information.  If one or more `<projname>` is given, narrow the action to just those projects.  A `--spack` CLI option or `spack` TOML variable for the env can name an existing path to a spack installation.

- `config capture [-o/--output outfile] [<what> ...]` will examine the current layout, possibly narrowed by `<what>` and produce TOML to the output file or to stdout if `-o/--output` is not given.  The `<what>` can be one or more paths in the panopoly area such as `source/`, `project/projX/`, `env/host/`, etc.

- `env enter [-e/--env <env>] <projname>` will cause the calling shell to "enter" the project in the environment placing the user in a shell in the `env/<env>/run/<proj>/` directory.  If `-e/--env` is not given, assume the env name "host".  An env that assumes a container will have a corresponding `image` variable in the config TOML.


Some open issues that need solving after gaining experience with the development

- What is the full configuration file schema?  Eventually, we want it be expressive enough to fully specify a panopoly area. 

- We want to be able to capture a panopoly area a configuration file and some information may need to be represented by the file system such as an env "image" name.

- How to provide help to "enter" an image?


