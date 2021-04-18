import os, subprocess, re
from io import StringIO
from glob import glob
import sqlite3

con = None

STD_RESOURCES = 10**9

TMPDIR="/var/tmp/sompyler/data"
SUBDIR="neusician"

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


def init_db(path):
    global con

    if os.path.getsize(path):
        print("Just establishing connection with "
             f"initialized database {path}."
            )
        con = sqlite3.connect(path)
        con.execute("PRAGMA FOREIGN_KEYS=ON")
        return
    else:
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


def register_user(name, password):

    c = con.cursor()
    c.execute("INSERT INTO user(name, password, given_resources)"
              "VALUES (?, ?, ?);", (name, password, STD_RESOURCES)
        )

    con.commit()

def get_hashed_password_of_user(name):

    c = con.cursor()
    try: return next(c.execute(
            "SELECT password FROM user WHERE name = ?", (name,)
        ))[0]
    except StopIteration:
        return None


def user_is_authenticated(name):

    c = con.cursor()
    c.execute("UPDATE user SET last_password_match=DATETIME('now')"
              " WHERE name=?", (name,)
        )
    con.commit()


def worker_directory_of_user(name, *path):

    c = con.cursor()
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

    return os.path.join(TMPDIR, '{:02d}'.format(worker_id), *path)


def initialize_sompyler(user, score):
    c = con.cursor()
    with open(worker_directory_of_user(user, "score"), "w") as score_fh:
        c.execute(
            "UPDATE worker SET taken_times=taken_times+1 "
            " WHERE userid=(SELECT ROWID FROM user WHERE name=?)",
            (user,)
        )
        for line in score:
            print(line, file=score_fh)
        con.commit()


def get_status(user):
    c = con.cursor()
    resources = next(c.execute("""
        SELECT given_resources - used_resources
          FROM user u
          JOIN worker w ON u.ROWID=w.userid
         WHERE u.name=?
        """, (user,)
    ))[0]
    sompyler_limits = os.environ["SOMPYLER_LIMITS"].replace(
        "::", f":{resources}:"
    )

    my_env = os.environ.copy()
    my_env["SOMPYLER_LIMITS"] = sompyler_limits

    try:
        res = subprocess.run(
          [ os.path.join(SUBDIR, "single-sompyler-procman.sh"),
            worker_directory_of_user(user), user
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
    new_res = int(new_res)

    if status:
        m = re.search(r"\S+\.\w+", status[0])
        if m:
            status = { 'file_accomplished': m.group(0) }
        else:
            status = { 'remaining_time': status[0] or remtime }

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
        errors = re.sub(r'(?:(")?\S+/)\.\.', '\\1...', errors)
        if '_TOTAL_LIMIT' in errors:
            errors = (
                    "You have used up your total samples quota. "
                    f"Can you restrict yourself to {resources} "
                    f"of originally {STD_RESOURCES}?"
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


def waiting_stats_for_user(user):
    c = con.cursor()
    wait_rank = next(c.execute("""
        SELECT wait_rank
          FROM waiting_users wu
          JOIN user u ON u.ROWID=wu.userid
         WHERE u.name=?
    """, (user,) ))[0]
    waiting = next(c.execute("SELECT count(*) FROM waiting_users"))[0]
    workers = next(c.execute("SELECT count(*) FROM worker"))[0]
    return { 'wait_rank': wait_rank, 'waiting': waiting, 'workers': workers }
