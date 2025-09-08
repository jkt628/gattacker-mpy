# gattacker-mpy - [gattacker] for [MicroPython]

[gattacker]: https://github.com/securing/gattacker
[MicroPython]: https://micropython.org

## One Time Setup

this version for [MicroPython] is used later in this doc and MUST be synchronized to the [Makefile].
[Makefile]: ./Makefile

```bash
MICROPYTHON_VERSION=1.26.0
```

several libraries and tools are required to build on your host and run on your microcontroller.
of course, you must [install MicroPython](https://micropython.org/download/) for your microcontroller(s).

* aioble - asyncio library for Bluetooth Low Energy
* esptool - burn firmware to ESP32 devices
* mpremote - interact with [MicroPython] device
* mpy-cross - precompile for faster loading
* uv - work around long outstanding [limitations in pip](https://github.com/pypa/pip/issues/11440)

this is how i installed, [YMMV](https://dictionary.cambridge.org/us/dictionary/english/ymmv).

```bash
brew install esptool make mpremote mpy-cross python uv
```

## IDE Support

[MicroPython stubs](https://github.com/Josverl/micropython-stubs) give the language server MicroPython specific details.
my microcontrollers are all based on esp32 but stubs for other configurations are available.

```bash
pip install -U micropython-esp32-stubs --no-user --target ./typings
wget -O- https://github.com/micropython/micropython-lib/archive/refs/tags/v${MICROPYTHON_VERSION}.tar.gz | \
tar xzf - -C typings \
--transform=s:micropython-lib-${MICROPYTHON_VERSION}/micropython/bluetooth/aioble/:: \
micropython-lib-${MICROPYTHON_VERSION}/micropython/bluetooth/aioble/aioble
```

## Prepare microcontroller

i have an [M5Stack Atom Matrix](https://docs.m5stack.com/en/core/ATOM%20Matrix), adjust the [Makefile] or set `MICROCONTROLLER` appropriately.

```bash
make flash
# make flash MICROCONTROLLER=ESP32_GENERIC
```

## INSTALL

the [Makefile] handles building and pushing the application to the microcontroller.
`/flash` acts as a pseudo path to the microcontroller filesystem, so `boot.py` is local and `/flash/boot.py` is remote.

```bash
make
```

### Secrets

[.gitignore](./.gitignore) avoids all files and directories which name contains _secrets_.
[envsubst](https://man7.org/linux/man-pages/man1/envsubst.1.html) processes all files as a way to avoid committing secrets in this repository.
i use [direnv](https://direnv.org) to put secrets in the environment and _envsubst_ puts the secrets in the installed files.
