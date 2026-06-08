import os, sys, stat, subprocess, json, re
from . import sompyler_procman as procman
from datetime import datetime
from random import Random
from .input_error import ScoreInputError
from .sompyler_yaml import make_yaml_code, code_analyzer
from .arbitextonotes import tones
from .arbitrarygrooves import preprocess as ag_preprocess
from .smart_indent import expand as indenter, unindent_from as unindenter
from .markov_util import MarkovSpecError
from .split_rhythmel import from_trinary

from flask import (
        Flask, render_template, request, jsonify, make_response, redirect,
        send_file, url_for
    )
from flask_httpauth import HTTPBasicAuth
from werkzeug import exceptions
from werkzeug.security import generate_password_hash, check_password_hash

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
    )

    auth = HTTPBasicAuth(realm="Even more private an area")

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
        if isinstance(number, float):
            number = str(round(number, 3))
        return number.replace(".", "<sup>.") + "</sup>"
 

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    print("NEUSICIAN_NEW_USER_REG_PREFIX="
        + app.config['NEUSICIAN_NEW_USER_REG_PREFIX'],
        file=sys.stderr)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    procman.TMPDIR = app.config["TMPDIR"]
    procman.SOMPYLER = app.config["SOMPYLER"]
    procman.EXT_PUBLISH_CMD = app.config.get("EXT_PUBLISH_CMD")
    limits = app.config.get("SOMPYLER_LIMITS")

    if limits:
        limits = limits.split(":")
        procman.STD_RESOURCES = int_wo_unit(limits[2])
        limits[2] = ''
        procman.SOMPYLER_LIMITS = ":".join(limits)
        del limits

    @app.before_request
    def init_db():
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
                        url_for('public-yaml-acceptor', **{'yamlcode-id': random_id}), code=303
                    )
                    scorefile.close()
                else:
                    return jsonify(plaintones)

            except MarkovSpecError as e:
                return "Markov specification invalid: " + str(e), 400

        else:
            markov = request.args.get("markov")
            if not markov:
                with open("neusician/markov_default.txt") as mfh:
                    markov = mfh.read()

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
            return render_template(
                    "401.tmpl", list_users=procman.who_never_logged_in()
                )

    def get_password_verifier():
        NEW_USER_REG_PREFIX = app.config["NEUSICIAN_NEW_USER_REG_PREFIX"]
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

    @app.route('/logout-user')
    @auth.login_required
    def logout_user():
        user = auth.current_user()
        procman.logout_user(user)
        return redirect(url_for('private-yaml-acceptor'), code=303)

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

    @app.route('/info')
    def limits():
        return render_template(
                "resources-info.tmpl",
                neusician={
                    'ver': subprocess.run([
                        "git", "describe"
                        ], capture_output=True, check=True
                    ).stdout.decode('utf-8'),
                    'diff': subprocess.run(["git", "diff"
                        ], capture_output=True, check=True
                    ).stdout.decode('utf-8')
                },
                sompyler={
                    'ver': subprocess.run([
                        "git", "-C", app.config["SOMPYLER"], "describe"
                        ], capture_output=True, check=True
                    ).stdout.decode('utf-8'),
                    'diff': subprocess.run([
                        "git", "-C", app.config["SOMPYLER"], "diff"
                        ], capture_output=True, check=True
                    ).stdout.decode('utf-8')
                },
                **procman.waiting_stats_for_user(None),
                limits=app.config.get("SOMPYLER_LIMITS").split(":")
            )

    @app.route('/chainfromnumbers', methods=('GET','POST'))
    def chain_from_numbers():
        if "decimal-melody" in request.form:
            melody = request.form.get("decimal-melody")
        else:
            melody = None
        props = {}
        if "decimal-rhythm" in request.form:
            decimal = request.form["decimal-rhythm"]
            if 'props-up' in request.form:
                props = {
                    'up': int(request.form.get("props-up") or 0),
                    'down': int(request.form.get("props-down") or 0),
                    'central': int(request.form.get("props-central") or 0),
                    'base': int(request.form.get("props-base") or 0),
                    'cycle_offset': int(request.form.get("props-offset") or 0),
                    'tick_offset': int(request.form.get("tick-offset") or 0),
                }
            elif melody:
                return 400, "Melody number not interpretable without props"
            output = from_trinary(
                int(decimal), (
                    request.form.get("segmentlen"),
                    request.form.get("chainlen", 0),
                    request.form.get("measurelen", 0)
                ),
                melody=melody, **props
            )
        else:
            output = None

        return render_template("sompyler-code-from-trinary.tmpl",
            current_value=request.form.get("decimal-rhythm", ""),
            segmentlen=(
                request.form.get("segmentlen", 0),
                request.form.get("chainlen", 0),
                request.form.get("measurelen", 0)
            ),
            props_up=props.get('up'), props_down=props.get('down'),
            props_central=props.get('central'),
            props_base=props.get('base'),
            props_offset=props.get('cycle_offset'),
            tick_offset=props.get('tick_offset'),
            decimal_melody=request.form.get("decimal-melody", ""),
            output_code=output
        )

    @app.route('/chaintool', methods=('GET',))
    def chaintool():
        return render_template("chain-tool.tmpl",
                    cols=int(request.args.get("cols", 12)),
                    rows=int(request.args.get("rows", 5)),
                    base=int(request.args.get("base", 0))
                )

    @app.route('/sompyle/reserved-a-worker-for-tests', methods=('GET', 'POST'), endpoint="private-yaml-acceptor")
    @auth.login_required
    @app.route('/sompyle', methods=('GET','POST'), endpoint='public-yaml-acceptor')
    def yaml_textarea():
        def _file_it():
            file_list = open(os.path.join(app.config["SOMPYLER"], "introspectables.txt"))
            for line in file_list:
                yield line.rstrip()
            file_list.close()

        if request.method == 'POST':
            user = auth.current_user()

            if "yamlcode" in request.form:
                yamlcode = indenter(request.form["yamlcode"])
                if request.form["action"] == 'delete':
                    if not next(yamlcode, None):
                        procman.delete_user_and_files(user)
                        return "Your session is erased.", 410
                    else:
                        return "yamlcode is not empty", 400
                if (m := re.search(r"\|[\[\s]|\n---", request.form["yamlcode"])):
                    score_pre_file = procman.worker_directory_of_user(user, "score.pre")
                    if "\n*** " in request.form["yamlcode"][:m.start()]:
                        yamlcode = ag_preprocess(yamlcode, out=open(score_pre_file, 'w'))
                    elif os.path.exists(score_pre_file.removesuffix("pre") + "txt"):
                        try:
                            os.unlink(score_pre_file)
                        except FileNotFoundError:
                            pass
                else:
                    return "yamlcode does not contain any measures", 400
                procman.initialize_sompyler(user, yamlcode)

            if request.form["action"] == "rawanalysis":
                return redirect(url_for('sompyler_static_code_analyzer'), code=303)

            status = procman.get_status(
                    user, request.form.get("w0mode", "ff"),
                    request.form.get("only-measures"),
                    quota=int(request.form.get("quota", 100)),
                    workers=app.config.get("WORKERS_PER_USER")
                )

            if status['frozen'] is True:
                if (score_file := procman.worker_directory_of_user(user, "score.pre")):
                    if os.path.exists(score_file):
                        os.rename(
                                score_file, score_file.removesuffix("pre") + "txt"
                            )
                if "file_accomplished" in status:
                    return redirect(url_for("send_audio_generated"), code=303)
                elif request.form.get("w0mode") == "midi":
                    return redirect(url_for("midi_exporter"), code=303)
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
                return redirect(url_for("sompyler_status_report"), code=303)
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
                for filename in ("score.txt", "score"):
                    score_file = procman.worker_directory_of_user(user, filename)
                    if os.path.exists(score_file): break
                try:
                    with open(score_file, "r") as fh:
                        yamlcode = fh.read()
                except FileNotFoundError:
                    pass
            return render_template("yaml-input.tmpl",
                yamlcode=yamlcode.rstrip(),
                user=user,
                quota=quota(user),
                limits=app.config.get("SOMPYLER_LIMITS"),
                interesting_files=_file_it()
            )

    @app.route('/sompyle/publish', methods=('GET',), endpoint='publisher')
    @auth.login_required
    def publish():
        user = auth.current_user()
        path = os.path.join(
              procman.TMPDIR, "OUT", f"{user}.mp3"
            )
        title = request.args.get("title")
        if os.path.exists(path):
            with open(
                    procman.worker_directory_of_user(user, "score"), "r"
                ) as score_file:
                for line in score_file:
                    if line == "title:\n":
                        title = ''
                    elif title is not None:
                        if line.isspace(): break
                        if line[0].isspace():
                            title = " ".join([title, line.strip()])
                        else: break
                    elif line.startswith("title: "):
                        title = line[7:].rstrip()
                        break
                    elif line.isspace() or not line:
                        break
            url = procman.publish_tarfile(
                    auth.current_user(), title or "No title"
                )
            return redirect(url, code=303)
        else:
            return "rendered mp3 does not exist", 404

    @app.route("/files/<idir>/<path:ifile>")
    def view_interesting_file(idir, ifile):
        if not (idir in ('lib', 'scores')
                and ifile[:-1].endswith(".spl")
                and "../" not in ifile
                ):
            return "This file is not listed, is it? So it probably does neither exist nor is of your business. ;)", 404
        ifile = os.path.join(app.config["SOMPYLER"], idir, ifile)
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
        with open(score_file) as score_fh:
            return render_template(
                "sompyler-status-report.tmpl",
                yamlcode=score_fh.read().rstrip(),
                publish="EXT_PUBLISH_CMD" in app.config,
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
        user = auth.current_user()
        score_file = procman.worker_directory_of_user(user, "score")
        return render_template(
            "sompyler-code-analyzer.tmpl",
            user=user,
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
                with open(score_file) as score_fh:
                    response.data = unindenter(score_fh).encode("utf-8")
                    return response
            else:
                return send_file(score_file, mimetype="text/plain")

    @app.route("/sompyle/result.mp3")
    @auth.login_required
    def send_audio_generated():
        return send_file(os.path.join(
              procman.TMPDIR, "OUT", f"{auth.current_user()}.mp3"
            ),
            mimetype="audio/mp3",
            max_age=0
        )

    @app.route("/sompyle/midi", methods=('GET', 'POST'))
    @auth.login_required
    def midi_exporter():
        user = auth.current_user()
        premidi_score = procman.worker_directory_of_user(user, "premidi.txt")
        procman.MIDIEXP = app.config['MIDIEXP']
        if not os.path.exists(premidi_score):
            return "Please render sompyler code to PREMIDI first", 424
        with open(premidi_score) as ps:
            voices = []
            for line in ps:
                if (m := re.match(r"# VOICE\(name=([\"'])(\w+)\1", line)):
                    voices.append(m.group(2))
                elif not voices: continue
                else: break
            else:
                raise RuntimeError("No voices defined or notes ever played")
            if request.method == 'GET':
                ps.seek(0)
                return render_template(
                    "sompyler-midi-export.tmpl",
                    user=user,
                    voices=voices,
                    premidi_score=ps.read(),
                )
            else:
                voices = " ".join(
                        request.form.get(v) for v in voices if v is not None
                    )
                ppqn = int(request.form.get('ppqn', 240))
                procman.midi_export(premidi_score, ppqn, voices)
                return send_file(
                    procman.worker_directory_of_user(user, "result.mid"),
                    mimetype="audio/midi",
                    max_age=0,
                )

    @app.route('/sompyle/astlog')
    @auth.login_required
    def get_static_astlog():
        return send_file(
            procman.worker_directory_of_user(auth.current_user(), 'ast.log'),
            mimetype='text/plain',
        )
    
    @app.route("/sompyle/render-shapes", methods=("GET", "POST"))
    @auth.login_required
    def render_shapes():
        shapes = []
        params = request.form if request.method == "POST" else request.args
        for s in range(4):
            s = 'shape' + str(s+1)
            if params.get(s):
                shapes.append(params[s])
        intersteps = params.get('intersteps') or 0
        written_file = procman.worker_directory_of_user(auth.current_user(), 'rendered-shapes.svg')
        if request.form:
            try:
                procman.call_external('render-shapes',
                    *shapes, f"--steps={intersteps}",
                    f"--outfile={written_file}"
                )
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode('utf-8')
                if (m := re.search(r"^(?=Sompyler\b)", stderr, re.MULTILINE)):
                    stderr = stderr[m.start():]
                raise exceptions.BadRequest(stderr)
            return send_file(
                    written_file,
                    mimetype="image/svg+xml",
                    max_age=0
                )
        else:
            return render_template('render-shapes.tmpl',
                shape1=(shapes[0] if shapes else ''),
                shape2=(shapes[1] if len(shapes) > 1 else ''),
                shape3=(shapes[2] if len(shapes) > 2 else ''),
                shape4=(shapes[3] if len(shapes) > 3 else ''),
                intersteps=intersteps,
            )
    @app.route("/sompyle/analyze/tone-<int:number>")
    @auth.login_required
    def analyze_tone(number):
        user = auth.current_user()
        proc = procman.call_external(
                'analyze-tone', '$USERDIR', str(number), user=user,
            )
        return render_template(
            "tone-analyzer.tmpl",
            user=user,
            number=number,
            **json.loads(proc.stdout)
        )

    @app.route("/sompyle/analyze/tone-<int:number>/sound")
    @auth.login_required
    def sound_of_tone(number):
        filename = procman.analyze_tone(auth.current_user(), number, "sound")
        return send_file(filename, mimetype="audio/ogg", max_age=0)

    @app.route("/sompyle/analyze/tone-<int:number>/outline")
    @auth.login_required
    def outline_of_tone(number):
        try:
            filename = procman.analyze_tone(auth.current_user(), number, "outline")
        except RuntimeError as e:
            if "Sompyler.limits" in str(e):
                return str(e).split("Sompyler.limits.")[1].rstrip("\\n\'\""), 400
            else: raise
        return send_file(filename, mimetype="image/png", max_age=0)

    @app.errorhandler(procman.NoWorkersAvailableError)
    def service_unavailable_for_user(exception):

        stats = {
            'workers': 3,
            'wait_rank': '?',
            'waiting': '?',
        }

        user = auth.current_user()
        stats.update(procman.waiting_stats_for_user(user))

        return render_template(
            "service-unavailable.tmpl",
            user=user,
            **stats
        ), 503

    @app.errorhandler(ScoreInputError)
    def preprocessor_error(exception):
        return render_template(
            "preprocessor-failed.tmpl",
            msg=str(exception),
            last_lines=exception.tail_log()
        ), 400

    @app.errorhandler(exceptions.BadRequest)
    def badrequest_error(exception):
        return render_template(
            "400.tmpl",
            error_message=exception.description
        ), 400
    
    @app.teardown_request
    def close_connection(exception):
        procman.close_connection()

    return app
