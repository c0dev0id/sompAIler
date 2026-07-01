REPO_ROOT     := $(abspath ..)
SOMPYLER_DIR  := $(REPO_ROOT)/sompyler
NEUSICIAN_DIR := $(REPO_ROOT)/neusician
VUE_APP_DIR   := $(REPO_ROOT)/AddOns/score_editors/vue3js-app

VENV   := $(CURDIR)/venv
PIP    := $(VENV)/bin/pip
PYTHON := $(VENV)/bin/python3
FLASK  := $(VENV)/bin/flask

TMPDIR_PATH    := $(CURDIR)/tmp
WORKER_IDS     := 00 01 02
WORKER_DIRS    := $(addprefix $(TMPDIR_PATH)/,$(WORKER_IDS)) $(TMPDIR_PATH)/OUT
NEUSICIAN_INST := $(CURDIR)/instance
DB             := $(NEUSICIAN_INST)/neusician.db

BASE_TMPL      := $(CURDIR)/templates/base.tmpl
BASE_TMPL_STUB := $(NEUSICIAN_DIR)/neusician/templates/base.tmpl.stub
AUDIOWIDGET      := $(CURDIR)/templates/vue3_neusik/audiowidget.tmpl
AUDIOWIDGET_STUB := $(VUE_APP_DIR)/templates/vue3_neusik/audiowidget.tmpl.stub

.PHONY: build serve clean

build: venv/.installed score_editors/vue3_neusik sompyler-run/scripts \
       $(WORKER_DIRS) $(NEUSICIAN_INST)/config.py $(BASE_TMPL) $(AUDIOWIDGET)

# ── python venv ───────────────────────────────────────────────────────────────

venv/.installed:
	python3 -m venv --system-site-packages $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(SOMPYLER_DIR)/requirements.txt
	$(PIP) install flask flask-httpauth
	$(PYTHON) -c "\
import sysconfig, pathlib; \
p = pathlib.Path(sysconfig.get_path('purelib')); \
(p / 'sompAIler.pth').write_text('$(NEUSICIAN_DIR)\n$(SOMPYLER_DIR)\n$(CURDIR)\n')"
	@touch $@

# ── score_editors package ─────────────────────────────────────────────────────

score_editors/__init__.py:
	mkdir -p score_editors
	touch $@

score_editors/vue3_neusik: score_editors/__init__.py
	ln -sf $(VUE_APP_DIR) $@

# ── sompyler synthesis wrapper ────────────────────────────────────────────────
# single-sompyler-procman.sh does: cd $SOMPYLER; . venv/bin/activate; ./scripts/sompyle
# We can't create venv/ inside the read-only sompyler submodule, so point
# SOMPYLER at this wrapper directory which symlinks both into place.

sompyler-run/scripts: venv/.installed
	mkdir -p sompyler-run
	ln -sf $(SOMPYLER_DIR)/scripts sompyler-run/scripts
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

$(BASE_TMPL):
	mkdir -p $(CURDIR)/templates
	cp $(BASE_TMPL_STUB) $@

$(AUDIOWIDGET):
	mkdir -p $(CURDIR)/templates/vue3_neusik
	cp $(AUDIOWIDGET_STUB) $@

# ── serve ─────────────────────────────────────────────────────────────────────

serve:
	$(FLASK) --app $(CURDIR)/wsgi.py run --port 5005

# ── clean ─────────────────────────────────────────────────────────────────────

clean:
	rm -rf venv score_editors sompyler-run tmp instance templates
