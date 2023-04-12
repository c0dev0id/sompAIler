import os, sys, stat, subprocess, json
from . import sompyler_procman as procman
from .arbitextonotes import tones
from .smart_indent import expand as indenter, unindent_from as unindenter
from datetime import datetime
from random import Random

import subprocess

def quota(user):
    q = procman.get_quota(user)
    return '{:.0f}'.format(
            q / procman.STD_RESOURCES * 100
        ) if q is not None else ''


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'neusician.db'),
        SERVER_NAME="demo.neusik.de",
        PREFERRED_URL_SCHEME="https",
    )

    auth = HTTPBasicAuth(realm="Even more private an area")

    print("NEUSICIAN_NEW_USER_REG_PREFIX="
        + os.environ['NEUSICIAN_NEW_USER_REG_PREFIX'],
        file=sys.stderr)

    def int_wo_unit(number): # integer with/without (w/o) units resolved
        # copied from Sompyler
        units = {'K': 3, 'M': 6, 'G': 9, 'T': 12}
        if (unit := number[-1]) in units:
            number = int(number[:-1]) * 10 ** units[unit]
        else:
            number = int(number)
        return number

    @app.template_filter('fsup')
    def sup_fractional(number):
        return f'{float(number):.3f}'.replace(".", "<sup>.") + "</sup>"
 

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    procman.TMPDIR = app.config["TMPDIR"]
    limits = app.config.get("SOMPYLER_LIMITS")

    if limits:
        limits = limits.split(":")
        procman.STD_RESOURCES = int_wo_unit(limits[2])
        limits[2] = ''
        procman.SOMPYLER_LIMITS = ":".join(limits)
        del limits
    procman.init_db(app.config["DATABASE"])

    @app.route('/', endpoint="index")
    def hello():
        return render_template("hello.tmpl")

    @app.route('/randomelody', methods=("GET", "POST"))
    def randomelody_stage1():
        if request.method == 'POST':
            seedphrase = request.form["seedphrase"]
            if len(seedphrase) > 1000:
                return "Seed phrase is too long", 400
            try:
                plaintones = tones(
                    request.form["seedphrase"],
                    request.form["markovspec"],
                    (int(request.form["melody-share"]),
                     int(request.form["pause-share"])),
                    restrict_88keys=bool(request.form.get("wrap-keys"))
                )
                if request.form.get("sompyler_init") not in ('', '0', None, 'None'):
                    sompyler_init = request.form["sompyler_init"].split("~")
                    try:
                        subdivisions = sompyler_init[1]
                    except:
                        raise RuntimeError("sompyler_init = " + repr(request.form["sompyler_init"]))
                    if len(subdivisions) == 1 and subdivisions.isdecimal():
                        subdivisions = [0] * int(subdivisions)
                        subdivisions[0] += 1
                    elif "." in subdivisions:
                        subdivisions = [
                                int(x) for x in subdivisions.split(".")
                            ]
                    elif "0" in subdivisions:
                        subdivisions = list(subdivisions)
                        yamlcode = make_yaml_code(
                            plaintones,
                            beats=[
                                int(x) for x in sompyler_init[0].split(".")
                            ] if "." in sompyler_init[0] else list(
                                sompyler_init[0]
                            ),
                            subdivisions=subdivisions,
                            cut=int(sompyler_init[2]),
                            beats_per_minute=int(sompyler_init[3]),
                            upper_stress_bound=int(sompyler_init[4]),
                            lower_stress_bound=int(sompyler_init[5])
                        ).getvalue()
                        random_id = Random().randrange(1,10000)
                        scorefile = open(f"/tmp/sompyled-{random_id}.yaml", "w")
                        print(yamlcode
                          + "\n# -------"
                          + "\n# You can reproduce above output simply by URL:"
                          + "\n# " + url_for('randomelody_stage1',
                              _external=True,
                            **{
                              'seedphrase': request.form["seedphrase"],
                              'markov': request.form["markovspec"],
                              'melody-share': request.form["melody-share"],
                              'pause-share': request.form["pause-share"],
                              'sompyler_init': request.form["sompyler_init"],
                              'wrap_keys': request.form.get("wrap-keys")
                            }),
                          file=scorefile)
                        os.chmod(scorefile.name, stat.S_IREAD)
                        return redirect(
                             f"/sompyle?yamlcode-id={random_id}", code=303
                        )
                else:
                    return jsonify(plaintones)

            except MarkovSpecError as e:
                return "Markov specification invalid: " + str(e), 400
        else:
            markov = request.args.get("markov")
            if not markov:
                markov = open("neusician/markov_default.txt").read()
            return render_template("random.tmpl",
                seed_phrase=request.args.get("seedphrase", "test"),
                markov_spec=markov,
                correction="(Not implemented, yet)",
                melody_pause_ratio=(
                    request.args.get("melody-share", 1),
                    request.args.get("pause-share", 1)
                ),
                sompyler_init=request.args.get("sompyler_init"),
                wrap_keys=request.args.get("wrap_keys", "no")
            )

    @auth.error_handler
    def UnAuthorized(status):
        if status == 401:
            return render_template("401.tmpl")

    def get_password_verifier():
        NEW_USER_REG_PREFIX = os.environ["NEUSICIAN_NEW_USER_REG_PREFIX"]
        def _v(username, password):
            if password.startswith(NEW_USER_REG_PREFIX):
                password = password[ len(NEW_USER_REG_PREFIX) : ]
                if not procman.get_hashed_password_of_user(username):
                    print(f"Registering new user {username}", file=sys.stderr)
                    procman.register_user(
                        username, generate_password_hash(password)
                    )

            else:
                stored_password = procman.get_hashed_password_of_user(username)
                if stored_password and check_password_hash(
                        stored_password, password
                    ):
                        procman.user_is_authenticated(username)
                        return username
                else:
                    print(f"Failed password attempt from user {username}", file=sys.stderr)

        return _v
    auth.verify_password(get_password_verifier())

    @app.route('/change-password', methods=("GET", "POST"))
    @auth.login_required
    def change_password():
        user = auth.current_user()
        if request.method == 'GET':
            return render_template("change-password-form.tmpl", user=user)
        else:
            stored_password = procman.get_hashed_password_of_user(user)
            old_password = request.form["oldpassword"]
            new_password = request.form["changetopw"]
            same_password = request.form["repeatpw"]
            if check_password_hash(stored_password, old_password):
                if new_password == same_password:
                    procman.set_password_of_user(
                        user, generate_password_hash(new_password)
                    )
                else:
                    return "Passwords are not identical", 400
            else:
                return "Old password is not identical with the stored one", 400
            return redirect(url_for("private-yaml-acceptor"), code=303)

    @app.route('/sompyle/limits-info')
    def limits():
        return render_template(
                "resources-limits-info.tmpl", 
                **procman.waiting_stats_for_user(None),
                limits=app.config.get("SOMPYLER_LIMITS").split(":")
            )

    @app.route('/sompyle/reserved-a-worker-for-tests', methods=('GET', 'POST'), endpoint="private-yaml-acceptor")
    @auth.login_required
    @app.route('/sompyle', methods=('GET','POST'), endpoint='public-yaml-acceptor')
    def yaml_textarea():
        def _file_it():
            file_list = open(os.path.join(os.environ["SOMPYLER"], "introspectables.txt"))
            for line in file_list:
                yield line.rstrip()

        if request.method == 'POST':
            user = auth.current_user()

            if "yamlcode" in request.form:
                yamlcode = indenter(request.form["yamlcode"])
                if request.form["action"] == 'delete':
                    if next(yamlcode, None) is None:
                        procman.delete_user_and_files(user)
                        return "Your session is erased.", 410
                    else:
                        return "Bad request", 400
                procman.initialize_sompyler(user, yamlcode)

            if request.form["action"] == "rawanalysis":
                return redirect("/sompyle/analyze", code=303)

            status = procman.get_status(
                    user, request.form.get("w0mode", "ff"),
                    int(request.form.get("quota", 100))
                )

            if status['frozen'] is True:
                if "file_accomplished" in status:
                    return redirect("/sompyle/result.ogg", code=303)
                elif "errors" in status:
                    response = make_response()
                    response.data = status["errors"] + (
                            "\nScore updated? These might be the warnings/"
                            "errors of previous run."
                        )
                    response.headers["Content-Type"] = \
                            "text/plain; charset=utf-8"
                    response.status_code = 409
                    return response
                else:
                    return "Missing score to synthesize", 409
            elif request.form["action"] == "sompyle":
                return redirect("/sompyle/status", code=303)
            else:
                return "Unknown action", 404

        else:
            user = None
            yamlcode = request.args.get("yamlcode", "")[:1000]
            if not yamlcode and "yamlcode-id" in request.args:
                try:
                    with open(f'/tmp/sompyled-{request.args["yamlcode-id"]}.yaml') as f:
                        yamlcode = f.read()
                        os.remove(f.name)
                except FileNotFoundError:
                    pass
            elif (user := auth.current_user()) and yamlcode == '':
                score_file = procman.worker_directory_of_user(user, "score")
                try:
                    with open(score_file, "r") as fh:
                        yamlcode = fh.read()
                except FileNotFoundError:
                    pass
            return render_template("yaml-input.tmpl",
                yamlcode=yamlcode,
                user=user,
                quota=quota(user),
                limits=app.config.get("SOMPYLER_LIMITS"),
                interesting_files=_file_it()
            )

    @app.route("/files/<idir>/<path:ifile>")
    def view_interesting_file(idir, ifile):
        if not (idir in ('lib', 'scores')
                and ifile[:-1].endswith(".spl")
                and "../" not in ifile
                ):
            return "This file is not listed, is it? So it probably does neither exist nor is of your business. ;)", 404
        ifile = os.path.join(os.environ["SOMPYLER"], idir, ifile)
        try:
            return send_file(ifile, mimetype="text/plain")
        except FileNotFoundError:
            return "File not found", 404

    @app.route("/sompyle/status")
    @auth.login_required
    def sompyler_status_report():
        user = auth.current_user()
        status = procman.get_status(user)
        status['timestamp'] = int(datetime.now().timestamp())
        score_file = procman.worker_directory_of_user(user, "score")
        return render_template(
            "sompyler-status-report.tmpl",
            yamlcode=open(score_file).read(),
            user=user,
            quota=quota(user),   
            **status
        )

    @app.route("/sompyle/status.json", endpoint='statusjson')
    @auth.login_required
    def sompyler_status_json():
        user = auth.current_user()
        status = procman.get_status(
                user, tail_log=request.args.get("tail-log", True)
            )
        if 'notes_log' in status:
            status['notes_log'] = [ line for line in status['notes_log'] ]
        return jsonify(status)

    @app.route("/sompyle/analyze")
    @auth.login_required
    def sompyler_static_code_analyzer():
        score_file = procman.worker_directory_of_user(auth.current_user(), "score")
        return render_template(
            "sompyler-code-analyzer.tmpl",
            json=code_analyzer(score_file)
        )

    @app.route("/sompyle/score.spls", methods=('GET', 'PUT'))
    @auth.login_required
    def plain_text_score():
        if request.method == 'PUT':
            if request.headers['Content-Type'].endswith('yaml'):
                from io import StringIO
                procman.initialize_sompyler(
                    auth.current_user(),
                    StringIO(request.get_data(as_text=True))
                )
                response = make_response()
                response.status_code = 202
                response.headers['Location'] = url_for('statusjson', _external=True)
                response.headers['Content-Type'] = 'text/plain'
                response.data = ("The document will be processed when the Location URL "
                                "(status monitoring) is called")
                return response
            else:
                return ("Expecting a proper YAML payload with "
                       "Content-Type header ending with 'yaml'",
                       400
                    )
        else:
            score_file = procman.worker_directory_of_user(
                    auth.current_user(), "score"
                )
            if request.args.get("concise"):
                response = make_response()
                response.headers['Content-Type'] = 'text/plain'
                response.data(unindenter(open(score_file)))
                return response
            else:
                return send_file(score_file, mimetype="text/plain")

    @app.route("/sompyle/result.ogg")
    @auth.login_required
    def send_audio_generated():
        return send_file(os.path.join(
              procman.TMPDIR, "OUT", f"{auth.current_user()}.ogg"
            ),
            mimetype="audio/ogg",
            cache_timeout=0
        )

    @app.route("/sompyle/analyze/tone-<int:number>")
    @auth.login_required
    def analyze_tone(number):
        proc = subprocess.run(
                ['analyze-tone',
                    procman.worker_directory_of_user(auth.current_user()), str(number)
                ], capture_output=True, check=True
            )
        return render_template(
            "tone-analyzer.tmpl",
            number=number,
            **json.loads(proc.stdout)
        )

    @app.route("/sompyle/analyze/tone-<int:number>/sound")
    @auth.login_required
    def sound_of_tone(number):
        filename = procman.analyze_tone(auth.current_user(), number, "sound")
        return send_file(filename, mimetype="audio/ogg", cache_timeout=0)

    @app.route("/sompyle/analyze/tone-<int:number>/outline")
    @auth.login_required
    def outline_of_tone(number):
        try:
            filename = procman.analyze_tone(auth.current_user(), number, "outline")
        except RuntimeError as e:
            if "Sompyler.limits" in str(e):
                return str(e).split("Sompyler.limits.")[1].rstrip("\\n\'\""), 400
            else: raise
        return send_file(filename, mimetype="image/png", cache_timeout=0)

    @app.errorhandler(procman.NoWorkersAvailableError)
    def service_unavailable_for_user(user):

        stats = {
            'workers': 3,
            'wait_rank': '?',
            'waiting': '?',
        }

        stats.update(procman.waiting_stats_for_user(auth.current_user()))

        return render_template(
            "service-unavailable.tmpl",
            **stats
        ), 503

    @app.teardown_appcontext
    def close_connection(exception):
        procman.close_connection()

    return app

if 'uwsgi' in sys.modules:
    from .sompyler_yaml import make_yaml_code, code_analyzer
    from .markov_util import MarkovSpecError
    from flask import (
            Flask, render_template, request, jsonify, make_response, redirect,
            send_file, url_for
        )
    from flask_httpauth import HTTPBasicAuth
    from werkzeug.security import generate_password_hash, check_password_hash
    app = create_app()
