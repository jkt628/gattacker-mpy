# gattacker-mpy - [gattacker] for [MicroPython]

[gattacker]: https://github.com/securing/gattacker
[MicroPython]: https://micropython.org

## One Time Setup

several libraries and tools are required to build on your host and run on your microcontroller.
of course, you must [install MicroPython](https://micropython.org/download/) for your microcontroller(s).

* mpremote - interact with [MicroPython] device
* mpy-cross - precompile for faster loading
* uv - work around long outstanding [limitations in pip](https://github.com/pypa/pip/issues/11440)

this is how i installed, [YMMV](https://dictionary.cambridge.org/us/dictionary/english/ymmv).

```bash
brew install make mpremote mpy-cross python uv
mpremote fs rm :main.py
```

## IDE Support

[MicroPython stubs](https://github.com/Josverl/micropython-stubs) give the language server MicroPython specific details.
my microcontrollers are all based on esp32 but stubs for other configurations are available.

```bash
pip install -U micropython-esp32-stubs --no-user --target ./typings
```

## INSTALL

the [Makefile](./Makefile) handles building and pushing the application to the microcontroller.
`/flash` acts as a pseudo path to the microcontroller filesystem, so `boot.py` is local and `/flash/boot.py` is remote.

```bash
make
```

### Secrets

[.gitignore](./.gitignore) avoids all files and directories which name contains _secrets_.
[envsubst](https://man7.org/linux/man-pages/man1/envsubst.1.html) processes all files as a way to avoid committing secrets in this repository.
i use [direnv](https://direnv.org) to put secrets in the environment and _envsubst_ puts the secrets in the installed files.
