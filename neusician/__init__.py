import os, sys, stat
from . import sompyler_procman as procman
from .arbitextonotes import tones
from .smart_indent import expand as indenter
from datetime import datetime
from random import Random

NEW_USER_REG_PREFIX = os.environ.get("NEUSICIAN_NEW_USER_REG_PREFIX", "+")

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

    print(f"NEUSICIAN_NEW_USER_REG_PREFIX={NEW_USER_REG_PREFIX}",
        file=sys.stderr)

    procman.init_db(app.config["DATABASE"])

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

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

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

    @auth.verify_password
    def verify_password(username, password):
        if username.startswith(NEW_USER_REG_PREFIX):
            username = username[ len(NEW_USER_REG_PREFIX) : ]
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

        return

    @app.route('/sompyle/reserved-a-worker-for-tests', methods=('GET', 'POST'))
    @auth.login_required
    @app.route('/sompyle', methods=('GET','POST'), endpoint='public-yaml-acceptor')
    def yaml_textarea():
        if request.method == 'POST':
            user = auth.current_user()
            yamlcode = indenter(request.form["yamlcode"])
            checkonly_flag = (
                    '?check-only=1' if 'check-only' in request.form
                                    else ''
                )
            procman.initialize_sompyler(user, yamlcode)
            if request.form["action"] == "sompyle":
                return redirect("/sompyle/status" + checkonly_flag)
            elif request.form["action"] == "rawanalysis":
                return redirect("/sompyle/analyze")
        else:
            user = False
            yamlcode = request.args.get("yamlcode", "")[:1000]
            if not yamlcode and "yamlcode-id" in request.args:
                try:
                    with open(f'/tmp/sompyled-{request.args["yamlcode-id"]}.yaml') as f:
                        yamlcode = f.read()
                        os.remove(f.name)
                except FileNotFoundError:
                    pass
            elif (user := auth.current_user()) and (
                    yamlcode == '' and request.args.get("undo", False)
                ):
                score_file = procman.worker_directory_of_user(user, "score")
                try:
                    with open(score_file, "r") as fh:
                        yamlcode = fh.read()
                except FileNotFoundError:
                    pass
            return render_template("yaml-input.tmpl",
                yamlcode=yamlcode,
                user=user
            )

    @app.route("/sompyle/status")
    @auth.login_required
    def sompyler_status_report():
        user = auth.current_user()
        check_only = request.args.get('check-only', False)
        status = procman.get_status(user, check_only)
        status['timestamp'] = int(datetime.now().timestamp())
        score_file = procman.worker_directory_of_user(user, "score")
        return render_template(
            "sompyler-status-report.tmpl",
            yamlcode=open(score_file).read(),
            **status
        )

    @app.route("/sompyle/status.json")
    @auth.login_required
    def sompyler_status_json():
        user = auth.current_user()
        check_only = request.args.get('check-only', False)
        status = procman.get_status(user, check_only, tail_log=True)
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

    @app.route("/sompyle/result.ogg")
    @auth.login_required
    def send_audio_generated():
        return send_file(os.path.join(
              procman.TMPDIR, "OUT", f"{auth.current_user()}.ogg"
            ),
            mimetype="audio/ogg",
            cache_timeout=0
        )

    @app.errorhandler(procman.NoWorkersAvailableError)
    def service_unavailable_for_user(user):
        stats = {
            'workers': 3,
            'wait_rank': '?',
            'waiting': '?',
            'resources': '?',
            'tone_length': '?',
            'total_play_length': '?',
            'cache_size': '?'
        }

        stats.update(procman.waiting_stats_for_user(auth.current_user()))

        return render_template(
            "service-unavailable.tmpl",
            **stats
        )

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
