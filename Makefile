PYTHON:=.venv/bin/python

.PHONY: install
install: \
  install-boot \
  install-libs \
  install-objs \
  install-main

.PHONY: install-venv
install-venv: ${PYTHON}
${PYTHON}:
	uv venv .venv

.PHONY: install-libs
install-libs: pyproject.toml install-venv
	uv pip install -r $<
	mkdir -p ${MD_LIB}

MD_SRC := .venv/lib/python*/site-packages/microdot
MD_LIB := lib/microdot
OBJS := \
  ${MD_LIB}/__init__.mpy \
  ${MD_LIB}/helpers.mpy \
  ${MD_LIB}/microdot.mpy \
  ${MD_LIB}/websocket.mpy
${MD_LIB}/%.mpy: ${MD_SRC}/%.py
	mpy-cross -o $@ $<

.PHONY: install-objs
install-objs: install-libs ${OBJS}
	mpremote fs cp -r lib :lib

.PHONY: install-main
install-main: /flash/main.py

.PHONY: install-boot
install-boot: /flash/boot.py

/flash/%.py: %.py
	envsubst <$< | mpremote fs cp /dev/stdin :$<
/flash/%.mpy: %.mpy
	mpremote fs cp $< :$<
%.mpy: %.py
	envsubst <$< | mpy-cross -o $@ -

.PHONY: clean
clean:
	find . -name "*.mpy" -exec rm {} +

.PHONY: distclean
distclean: clean
	rm -rf .venv
