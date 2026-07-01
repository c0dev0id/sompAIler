NEUSICIAN_URL := https://gitlab.com/flowdy/neusician/-/archive/master/neusician-master.tar.gz?ref_type=heads
SOMPYLER_URL  := https://gitlab.com/flowdy/sompyler/-/archive/master/sompyler-master.tar.gz?ref_type=heads
VUE_APP_URL   := https://git.uugrn.org/flow/vue3js-app-proposal-for-sdk-claude/archive/master.tar.gz

VENV   := $(CURDIR)/venv
PIP    := $(VENV)/bin/pip
PYTHON := $(VENV)/bin/python3
FLASK  := $(VENV)/bin/flask

SOMPYLER_SRC  := $(CURDIR)/src/sompyler
NEUSICIAN_SRC := $(CURDIR)/src/neusician
VUE_APP_SRC   := $(CURDIR)/src/vue3js-app

TMPDIR_PATH := $(CURDIR)/tmp
WORKER_IDS  := 00 01 02
WORKER_DIRS := $(addprefix $(TMPDIR_PATH)/,$(WORKER_IDS)) $(TMPDIR_PATH)/OUT

NEUSICIAN_INST   := $(CURDIR)/instance
DB               := $(NEUSICIAN_INST)/neusician.db
BASE_TMPL        := $(CURDIR)/templates/base.tmpl
BASE_TMPL_STUB   := $(NEUSICIAN_SRC)/neusician/templates/base.tmpl.stub
AUDIOWIDGET      := $(CURDIR)/templates/vue3_neusik/audiowidget.tmpl
AUDIOWIDGET_STUB := $(VUE_APP_SRC)/templates/vue3_neusik/audiowidget.tmpl.stub

.PHONY: build serve clean

build: venv/.installed neusician score_editors/vue3_neusik sompyler-run/scripts \
       $(WORKER_DIRS) $(NEUSICIAN_INST)/config.py $(BASE_TMPL) $(AUDIOWIDGET)

# ── download sources ──────────────────────────────────────────────────────────

src/neusician/.stamp:
	mkdir -p src/neusician
	ftp -o - "$(NEUSICIAN_URL)" | tar -C src/neusician --strip-components=1 -xzf -
	@touch $@

src/sompyler/.stamp:
	mkdir -p src/sompyler
	ftp -o - "$(SOMPYLER_URL)" | tar -C src/sompyler --strip-components=1 -xzf -
	@touch $@

src/vue3js-app/.stamp:
	mkdir -p src/vue3js-app
	ftp -o - "$(VUE_APP_URL)" | tar -C src/vue3js-app --strip-components=1 -xzf -
	@touch $@

# ── python venv ───────────────────────────────────────────────────────────────

venv/.installed: src/sompyler/.stamp
	python3 -m venv --system-site-packages $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(SOMPYLER_SRC)/requirements.txt
	$(PIP) install flask flask-httpauth
	$(PYTHON) -c "\
import sysconfig, pathlib; \
p = pathlib.Path(sysconfig.get_path('purelib')); \
(p / 'sompAIler.pth').write_text('$(CURDIR)\n')"
	@touch $@

# ── neusician package symlink ─────────────────────────────────────────────────
# procman uses SUBDIR="neusician" to locate schema.sql relative to CWD.
# Symlinking the inner package dir here makes that resolve correctly.

neusician: src/neusician/.stamp
	ln -sf $(NEUSICIAN_SRC)/neusician $@

# ── score_editors package ─────────────────────────────────────────────────────

score_editors/__init__.py:
	mkdir -p score_editors
	touch $@

score_editors/vue3_neusik: score_editors/__init__.py src/vue3js-app/.stamp
	ln -sf $(VUE_APP_SRC) $@

# ── sompyler synthesis wrapper ────────────────────────────────────────────────
# single-sompyler-procman.sh does: cd $SOMPYLER; . venv/bin/activate; ./scripts/sompyle
# We can't create venv/ inside the downloaded sompyler source, so point
# SOMPYLER at this wrapper directory which symlinks both into place.

sompyler-run/scripts: venv/.installed src/sompyler/.stamp
	mkdir -p sompyler-run
	ln -sf $(SOMPYLER_SRC)/scripts sompyler-run/scripts
	ln -sf $(VENV) sompyler-run/venv

# ── worker + output directories ───────────────────────────────────────────────

$(WORKER_DIRS):
	mkdir -p $@

# ── database ──────────────────────────────────────────────────────────────────

$(DB): $(WORKER_DIRS)
	mkdir -p $(NEUSICIAN_INST)
	touch $(DB)

$(NEUSICIAN_INST)/config.py: $(DB)
	printf '%s\n' \
	    "SECRET_KEY = 'dev-only-change-for-production'" \
	    "DATABASE = '$(DB)'" \
	    "NEUSICIAN_NEW_USER_REG_PREFIX = 'register:'" \
	    "SOMPYLER = '$(CURDIR)/sompyler-run'" \
	    "TMPDIR = '$(TMPDIR_PATH)'" \
	    "SCORE_EDITOR_BLUEPRINT = 'vue3_neusik'" \
	    > $@

# ── template stubs ────────────────────────────────────────────────────────────

$(BASE_TMPL): src/neusician/.stamp
	mkdir -p $(CURDIR)/templates
	cp $(BASE_TMPL_STUB) $@

$(AUDIOWIDGET): src/vue3js-app/.stamp
	mkdir -p $(CURDIR)/templates/vue3_neusik
	cp $(AUDIOWIDGET_STUB) $@

# ── serve ─────────────────────────────────────────────────────────────────────

serve:
	$(FLASK) --app $(CURDIR)/wsgi.py run --port 5005

# ── clean ─────────────────────────────────────────────────────────────────────

clean:
	rm -rf venv src neusician score_editors sompyler-run tmp instance templates
