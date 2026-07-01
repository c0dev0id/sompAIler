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

NEUSICIAN_INST   := $(NEUSICIAN_SRC)/instance
DB               := $(NEUSICIAN_INST)/neusician.db
BASE_TMPL        := $(NEUSICIAN_SRC)/neusician/templates/base.tmpl
BASE_TMPL_STUB   := $(NEUSICIAN_SRC)/neusician/templates/base.tmpl.stub
AUDIOWIDGET      := $(VUE_APP_SRC)/templates/vue3_neusik/audiowidget.tmpl
AUDIOWIDGET_STUB := $(VUE_APP_SRC)/templates/vue3_neusik/audiowidget.tmpl.stub

STATIC        := $(NEUSICIAN_SRC)/neusician/static
JQUERYUI_DIR  := $(STATIC)/jquery-ui-1.12.1.custom
JQUERY_URL    := https://code.jquery.com/jquery-3.5.1.min.js
JQUERYUI_JS   := https://code.jquery.com/ui/1.12.1/jquery-ui.js
JQUERYUI_CSS  := https://code.jquery.com/ui/1.12.1/themes/smoothness/jquery-ui.css

.PHONY: build serve clean

build: venv/.installed neusician score_editors/vue3_neusik sompyler-run/scripts \
       $(WORKER_DIRS) $(NEUSICIAN_INST)/config.py $(BASE_TMPL) $(AUDIOWIDGET) \
       $(STATIC)/jquery-3.5.1.min.js $(JQUERYUI_DIR)/jquery-ui.js $(JQUERYUI_DIR)/jquery-ui.min.css

# ── download sources ──────────────────────────────────────────────────────────

src/neusician/.stamp:
	mkdir -p src
	ftp -o src/_dl.tgz "$(NEUSICIAN_URL)"
	tar -C src -xzf src/_dl.tgz
	rm -rf src/neusician
	mv src/neusician-master src/neusician
	rm src/_dl.tgz
	@touch $@

src/sompyler/.stamp:
	mkdir -p src
	ftp -o src/_dl.tgz "$(SOMPYLER_URL)"
	tar -C src -xzf src/_dl.tgz
	rm -rf src/sompyler
	mv src/sompyler-master src/sompyler
	rm src/_dl.tgz
	@touch $@

src/vue3js-app/.stamp:
	mkdir -p src
	ftp -o src/_dl.tgz "$(VUE_APP_URL)"
	tar -C src -xzf src/_dl.tgz
	rm src/_dl.tgz
	rm -rf src/vue3js-app
	cd src && for d in vue3js-app-*/; do mv "$$d" vue3js-app; break; done
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
# Flask is invoked with --app src/neusician/wsgi.py, making src/neusician/ the
# CWD, so neusician/schema.sql resolves to src/neusician/neusician/schema.sql.
# The symlink here makes "import neusician" work with dev-testserver/ on sys.path.

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

sompyler-run/scripts: venv/.installed src/sompyler/.stamp
	mkdir -p sompyler-run
	ln -sf $(SOMPYLER_SRC)/scripts sompyler-run/scripts
	ln -sf $(VENV) sompyler-run/venv
	touch sompyler-run/introspectables.txt

# ── worker + output directories ───────────────────────────────────────────────

$(WORKER_DIRS):
	mkdir -p $@

# ── database ──────────────────────────────────────────────────────────────────

$(DB): $(WORKER_DIRS) src/neusician/.stamp
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
	cp $(BASE_TMPL_STUB) $@

$(AUDIOWIDGET): src/vue3js-app/.stamp
	cp $(AUDIOWIDGET_STUB) $@

# ── static assets (not shipped with neusician) ────────────────────────────────

$(STATIC)/jquery-3.5.1.min.js: src/neusician/.stamp
	ftp -o $@ "$(JQUERY_URL)"

$(JQUERYUI_DIR)/jquery-ui.js: src/neusician/.stamp
	mkdir -p $(JQUERYUI_DIR)
	ftp -o $@ "$(JQUERYUI_JS)"

$(JQUERYUI_DIR)/jquery-ui.min.css: src/neusician/.stamp
	mkdir -p $(JQUERYUI_DIR)
	ftp -o $@ "$(JQUERYUI_CSS)"

# ── serve ─────────────────────────────────────────────────────────────────────

serve:
	$(FLASK) --app $(NEUSICIAN_SRC)/wsgi.py run --port 5005 --without-threads

# ── clean ─────────────────────────────────────────────────────────────────────

clean:
	rm -rf venv src neusician score_editors sompyler-run tmp
