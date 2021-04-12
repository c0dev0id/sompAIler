import os
from . import sompyler_procman as procman
from .arbitextonotes import tones
from .sompyler_yaml import make_yaml_code
from .markov_util import MarkovSpecError
from flask import Flask, render_template, request, jsonify, make_response, redirect, send_file
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'neusician.db'),
    )

    auth = HTTPBasicAuth(realm="Even more private an area")

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
                     int(request.form["pause-share"]))
                    )
                if "sompyler_init" in request.form:
                    sompyler_init = request.form["sompyler_init"].split("~")
                    subdivisions = sompyler_init[1]
                    if subdivisions.isdecimal():
                        subdivisions = [0] * int(subdivisions)
                        subdivisions[0] += 1
                    elif "." in subdivisions:
                        subdivisions = [ int(x) for x in subdivisions.split(".") ]
                    response = make_response(
                        make_yaml_code(
                            plaintones,
                            beats=[
                                int(x) for x in sompyler_init[0].split(".")
                            ],
                            subdivisions=subdivisions,
                            cut=int(sompyler_init[2]),
                            beats_per_minute=int(sompyler_init[3]),
                            upper_stress_bound=int(sompyler_init[4]),
                            lower_stress_bound=int(sompyler_init[5])
                       ).getvalue(), 200)
                    response.mimetype="text/plain"
                    return response
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
                sompyler_init=request.args.get("sompyler_init")
            )

    @auth.error_handler
    def UnAuthorized(status):
        if status == 401:
            return render_template("401.tmpl")

    @auth.verify_password
    def verify_password(username, password):
        if username.startswith("+"):
            if not procman.get_hashed_password_of_user(username[1:]):
                procman.register_user(
                    username[1:],
                    generate_password_hash(password)
                )

        else:
            stored_password = procman.get_hashed_password_of_user(username)
            if stored_password and check_password_hash(
                    stored_password, password
                ):
                    procman.user_is_authenticated(username)
                    return username

        return

    @app.route('/sompyle', methods=('GET','POST'))
    @auth.login_required
    def yaml_textarea():
        user = auth.current_user()
        if request.method == 'POST':
            if request.form["action"] == "sompyle":
                yamlcode = request.form["yamlcode"]
                procman.initialize_sompyler(user, yamlcode)
                return redirect("/sompyle/status")
        else: return render_template("yaml-input.tmpl",
                yamlcode=request.args.get("yamlcode")
            )

    @app.route("/sompyle/status")
    @auth.login_required
    def sompyler_status_report():
        user = auth.current_user()
        return render_template(
            "sompyler-status-report.tmpl",
            **procman.get_status(user)
        )

    @app.route("/sompyle/result.ogg")
    @auth.login_required
    def send_audio_generated():
        return send_file(os.path.join(
              procman.TMPDIR, "OUT", f"{auth.current_user()}.ogg"
            ),
            mimetype="audio/ogg"
        )

    return app

app = create_app()
