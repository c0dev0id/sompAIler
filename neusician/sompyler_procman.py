import os, subprocess, re
from io import StringIO
from glob import glob
import sqlite3, json

con = None
con_path = None

STD_RESOURCES = 10**9
SOMPYLER = None
SOMPYLER_LIMITS = None
SUBDIR="neusician"
TMPDIR=os.environ.get("TMPDIR", "/tmp")

class NoWorkersAvailableError(RuntimeError):
    pass

def register_worker(worker_id):

    wdir = os.path.join(TMPDIR, '{:02d}'.format(int(worker_id)))
    if not (os.path.isdir(wdir) and os.access(wdir, os.X_OK|os.W_OK)):
        raise FileNotFoundError(
                f"worker directory {path} not existent and writable"
            )

    c = con.cursor()
    c.execute("INSERT OR IGNORE INTO worker(id) VALUES (?)", (worker_id,))

def _get_cursor():
    global con
    first_time = True
    while first_time:
        try:
            c = con.cursor()
            first_time = False
        except AttributeError as e:
            if first_time is True:
                con = sqlite3.connect(con_path)
                con.execute("PRAGMA FOREIGN_KEYS=ON")
                first_time = -1
            else:
                raise
    return c

def close_connection():
    global con
    if con is not None: con.close()
    con = None


def init_db(path):
    global con, con_path
    con_path = path

    if os.path.getsize(path):
        con = sqlite3.connect(path)
        con.execute("PRAGMA FOREIGN_KEYS=ON")
        return

    print("Initializing fresh database "
         f"at path {path}."
        )
    con = sqlite3.connect(path)

    c = con.cursor()
    c.executescript(open(os.path.join(SUBDIR, "schema.sql")).read())

    wid = 0
    for wdir in glob(os.path.join(TMPDIR, '[0-9][0-9]')):
        wid = wdir.rsplit('/', 1)[1]
        try:
            register_worker(wid)
        except FileNotFoundError as e:
            print(e)

    con.commit()
    close_connection()


def register_user(name, password):

    c = _get_cursor()
    c.execute("INSERT INTO user(name, password, given_resources)"
              "VALUES (?, ?, ?);", (name, password, STD_RESOURCES)
        )

    con.commit()


def set_password_of_user(name, password):

    c = _get_cursor()
    c.execute("UPDATE user SET password=? WHERE name=?;", (password, name))

    con.commit()


def get_hashed_password_of_user(name):

    c = _get_cursor()
    try: return next(c.execute(
            "SELECT password FROM user WHERE name = ?", (name,)
        ))[0]
    except StopIteration:
        return None


def user_is_authenticated(name):

    c = _get_cursor()
    c.execute("UPDATE user SET last_password_match=DATETIME('now')"
              " WHERE name=?", (name,)
        )
    con.commit()


def worker_directory_of_user(name, *path):

    c = _get_cursor()
    try:
        worker_id = next(c.execute("""
            SELECT id
              FROM worker w
              JOIN user u ON w.userid=u.ROWID
             WHERE u.name=?
            """,
            (name,)
        ))[0]
    except StopIteration as e:
        rank = next(c.execute("""
            SELECT wait_rank
              FROM waiting_users
              JOIN user u ON userid=u.ROWID
             WHERE u.name=?
            """,
            (name,)
        ))[0]
        raise NoWorkersAvailableError(
                f"{rank-1} users preceed in queue".format(rank)
            ) from e

    def opath(fname):
        return os.path.join(
                TMPDIR, '{:02d}'.format(worker_id), *path[:-1], fname
            )

    if not path:
        return os.path.join(TMPDIR, '{:02d}'.format(worker_id), *path)

    elif path[-1] == 'score':
        # If score has not been created by requesting user, delete the score
        # unrevokably, otherwise it would be a breach of privacy.
        try:
            was_user = next(open(opath("worker.pid"), "r")).split()[0]
            if was_user != name: open(opath(path[-1]), 'w').close()
        except (FileNotFoundError, StopIteration):
            pass

    return opath(path[-1])


def delete_user_and_files(name):
    c = con.cursor()
    wdir = worker_directory_of_user(name)
    c.execute("DELETE FROM user WHERE name=?", (name,))
    for filename in os.listdir(wdir):
        os.unlink(os.path.join(wdir, filename))
    try:
        os.unlink(os.path.join(wdir, "..", "OUT", f"{name}.mp3"))
    except FileNotFoundError:
        pass

    con.commit()

def initialize_sompyler(user, score):
    c = _get_cursor()
    with open(worker_directory_of_user(user, "score"), "w") as score_fh:
        c.execute(
            "UPDATE worker SET taken_times=taken_times+1 "
            " WHERE userid=(SELECT ROWID FROM user WHERE name=?)",
            (user,)
        )
        for line in score:
            print(line, file=score_fh)
        con.commit()


def get_quota(user, c=None):
    if c is None:
        c = _get_cursor()
    return next(c.execute("""
        SELECT given_resources - used_resources
          FROM user u
          JOIN worker w ON u.ROWID=w.userid
         WHERE u.name=?
        """, (user,)
    ), (None,))[0]

def get_status(user, w0mode='ff', tail_log=False, quota=100, workers=None):
    c = _get_cursor()
    resources = get_quota(user, c)
    sompyler_limits = SOMPYLER_LIMITS.replace(
            "::",
            f":{min(resources,int(quota/100*STD_RESOURCES))}:"
        )

    my_env = os.environ.copy()
    my_env["SOMPYLER_LIMITS"] = sompyler_limits
    my_env["SKIP_KNOWN_LINES"] = str(1 if tail_log else '')
    my_env["SOMPYLER"] = SOMPYLER
    if workers is not None:
        my_env["WORKERS_PER_USER"] = str(workers)

    if w0mode is not None:
        my_env["W0MODE"] = w0mode
    else:
        raise RuntimeError("no w0mode")

    wdir = worker_directory_of_user(user)

    try:
        res = subprocess.run(
          [ os.path.join(SUBDIR, "single-sompyler-procman.sh"),
            wdir, user
          ], env=my_env, capture_output=True, check=True
        )
    except subprocess.CalledProcessError as e:
        log = open("/tmp/shell_out.log", "wb")
        log.write(e.stderr)
        log.close()
        raise

    notes, status, errors = res.stdout.decode("utf-8").split("---\n")

    progress, *status = status.split("\n")
    current, reused, total, remtime, new_res = progress.split()
    new_res = int(float(new_res))

    if status:
        m = re.search(r"\S+\.\w+", status[0])
        if m:
            status = { 'file_accomplished': True }
            status['frozen'] = True
        else:
            text_progress = status[0] or remtime
            if text_progress == '(loading...)':
                text_progress = 'Reading YAML score source ...'
            if text_progress.startswith('(ETA4RS'):
                text_progress = text_progress.replace(
                        '(ETA4RS', 'Reverb and Assembling ... (')
            elif text_progress.startswith('(ETA'):
                text_progress = text_progress.replace(
                        '(ETA', 'Synthesizing tones ... ('
                    )
            status = {'remaining_time': text_progress }
            status['frozen'] = '...' not in status['remaining_time']

    if new_res: # We ensure externally that res > 0 only once, just
            # the next call after having the audio file been
            # generated.
        c.execute("""
            UPDATE worker SET used_resources=used_resources+?
            WHERE userid=(SELECT ROWID FROM user WHERE name=?)
        """,
            (new_res, user)
        )
        resources -= new_res
        con.commit()

    if errors:
        errors = re.sub(r'(")?\S+/[Ss]ompyler[/.]*', '\\1.../', errors)
        if 'QuotaUsedUpError' in errors:
            errors = (
                    "Sorry, you have used up your total samples quota. "
                    "\nNow, at the latest, better save the score locally. "
                    "In 3h from now, without you accessing this service, "
                    "your account and all associate data is either removed "
                    "or your quota is restored to 100% upon log-in."
                    "\nYou can also purge the session and signup again. "
                    "This would erase the score and all data immediately. "
                    "You are welcome to sign-up anew using the told method."
                )

    return {
        'notes_log': StringIO(notes),
        'currently_rendered_notes': int(current),
        'notes_in_total': int(total),
        'reused': int(reused),
        'total_samples_calculated': '{:.01f}'.format(
            resources / STD_RESOURCES * 100
        ),
        **status,
        'errors': errors,
    }

def analyze_tone(user, tone_number, what_to_return):

    if what_to_return == "outline":
        c = _get_cursor()
        resources = get_quota(user, c)
        sompyler_limits = SOMPYLER_LIMITS.replace(
                "::",
                f":{resources}:"
            )
        my_env = os.environ.copy()
        my_env["SOMPYLER_LIMITS"] = sompyler_limits
        flag = f"--outline"
    elif what_to_return == "sound":
        flag = f"--sound"
        my_env = os.environ
    else:
        raise RuntimeError(f"{what_to_return} not supported")

    try:
        proc = subprocess.run(
                ['analyze-tone',
                    worker_directory_of_user(user), str(tone_number), flag
                ], env=my_env, capture_output=True, check=True
            )
        stdout = proc.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr)
    else:
        jsonstr = proc.stdout.decode("utf8").split("\n")[-2]
        stdout = json.loads(jsonstr)

    if (new_res := stdout.get("calculated_samples")):
            # We ensure externally that res > 0 only once, just
            # the next call after having the audio file been
            # generated.
        c.execute("""
            UPDATE worker SET used_resources=used_resources+?
            WHERE userid=(SELECT ROWID FROM user WHERE name=?)
        """,
            (new_res, user)
        )
        resources -= new_res
        con.commit()

    return stdout["file"]

def waiting_stats_for_user(user):
    c = _get_cursor()
    wait_rank = next(c.execute("""
        SELECT wait_rank
          FROM waiting_users wu
          JOIN user u ON u.ROWID=wu.userid
         WHERE u.name=?
    """, (user,) ), (None,))[0]
    waiting = next(c.execute("SELECT count(*) FROM waiting_users"))[0]
    workers = next(c.execute("SELECT count(*) FROM worker"))[0]
    return { 'wait_rank': wait_rank, 'waiting': waiting, 'workers': workers }

def who_never_logged_in():
    c = _get_cursor()
    it = c.execute("SELECT name FROM user WHERE last_password_match IS NULL")
    users = []
    for (u,) in it: users.append(u)
    return ", ".join(users) if users else "(none)"
